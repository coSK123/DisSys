from aio_pika import IncomingMessage
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from common.mq_service import RabbitMQService
from common.types import Message, OrderStatus, ServiceException
from common.monitoring import monitor_message_processing
import json
from typing import Dict, Optional
from datetime import datetime
import uuid
from pydantic import BaseModel
import structlog
from prometheus_client import Counter, make_asgi_app
import logging
from common.config import Config

# Initialize FastAPI app
app = FastAPI(title="Döner Order System")
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Metrics
websocket_connections = Counter('websocket_connections_total', 'Number of WebSocket connections')
websocket_disconnections = Counter('websocket_disconnections_total', 'Number of WebSocket disconnections')

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration Management
class ApiServiceSettings:
    rabbitmq_url: str = Config.get_rabbitmq_url()
    service_name: str = "api_service"
    update_queues: list[str] = ["order_supplied", "doener_supplied", "invoice_supplied"]

settings = ApiServiceSettings()

# Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.logger = structlog.get_logger()
        
    async def connect(self, order_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[order_id] = websocket
        websocket_connections.inc()
        self.logger.info("websocket_connected", order_id=order_id)
        
    def disconnect(self, order_id: str):
        if order_id in self.active_connections:
            del self.active_connections[order_id]
            websocket_disconnections.inc()
            self.logger.info("websocket_disconnected", order_id=order_id)
            
    async def send_update(self, order_id: str, message: dict):
        if order_id in self.active_connections:
            try:
                await self.active_connections[order_id].send_json(message)
                self.logger.info("update_sent", order_id=order_id, message_type=message.get('message_type'))
            except Exception as e:
                self.logger.error("send_update_failed", order_id=order_id, error=str(e))
                self.disconnect(order_id)
        else:
            self.logger.warning("can't update user, order id not found in active websocket connections", order_id=order_id)

manager = ConnectionManager()

# Request Models
class OrderRequest(BaseModel):
    customer_id: str
    details: Optional[Dict] = None

# Dependency for RabbitMQ
def get_rabbitmq_service() -> RabbitMQService:
    mq = app.state.rabbitmq_service

    if not mq or not mq.connection or not mq.connection.connected:
        raise HTTPException(status_code=503, detail="Message queue service unavailable")
    return mq

# Message Handlers
@monitor_message_processing('api_service')
async def handle_order_update(message: dict):
    """Handle updates from various services and forward to WebSocket"""
    order_id = message.get("order_id")
    if not order_id:
        raise ServiceException(message="Missing order_id in message", details=message)
    await manager.send_update(order_id, message)

async def message_handler(message: IncomingMessage):

    try:
        message_body = json.loads(message.body.decode("utf-8"))
        await handle_order_update(message_body)
        await message.ack()
    except Exception as e:
        logger.error("message_processing_failed")
        await message.nack(requeue=True)
        raise

@app.on_event("startup")
async def startup_event():
    """Startup event for initializing RabbitMQ"""
    
    logger.info("Starting Frontend Service...")
    
    mq_service = RabbitMQService(settings.service_name, settings.rabbitmq_url)
    await mq_service.initialize()

    app.state.rabbitmq_service = mq_service
    
    for queue_name in settings.update_queues:
        await mq_service.consume(queue_name, message_handler)
    
    logger.info("Frontend Service started successfully")

@app.post("/order/doener")
async def create_order(order: OrderRequest, mq_service: RabbitMQService = Depends(get_rabbitmq_service)):
    """Create a new döner order"""
    order_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    
    message = Message(
        correlation_id=correlation_id,
        order_id=order_id,
        timestamp=datetime.now(),
        message_type="ORDER_CREATED",
        payload={
            "customer_id": order.customer_id,
            "status": OrderStatus.CREATED.value,
            "details": order.details
        }
    )
    
    message_json = message.to_json()
    await mq_service.publish("order_requests", message_json)
    
    return {
        "order_id": order_id,
        "correlation_id": correlation_id,
        "websocket_url": f"/ws/{order_id}",
        "status": "created"
    }

@app.get("/health")
async def get_status(mq_service: RabbitMQService = Depends(get_rabbitmq_service)):
    """Get service status"""
    rabbitmq_status = "connected" if mq_service.connection and mq_service.connection.connected else "disconnected"
    return {"status": "healthy", "rabbitmq_status": rabbitmq_status}

@app.websocket("/ws/{order_id}")
async def websocket_endpoint(websocket: WebSocket, order_id: str):
    await manager.connect(order_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(order_id)

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event for closing RabbitMQ connection"""
    mq_service = app.state.rabbitmq_service
    if mq_service:
        await mq_service.close()
    for order_id in list(manager.active_connections.keys()):
        manager.disconnect(order_id)
