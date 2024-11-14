from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from common.message_queue import RabbitMQ
from common.types import Message, OrderStatus, ServiceException
from common.monitoring import setup_monitoring, monitor_message_processing
import json
import asyncio
from typing import Dict, Optional
from datetime import datetime
import uuid
from pydantic import BaseModel
import structlog
from prometheus_client import Counter



# Initialize FastAPI app
app = FastAPI(title="Döner Order System")
mq = RabbitMQ()
logger = setup_monitoring(app, 'frontend_service')


# Metrics
websocket_connections = Counter('websocket_connections_total', 'Number of WebSocket connections')
websocket_disconnections = Counter('websocket_disconnections_total', 'Number of WebSocket disconnections')

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

manager = ConnectionManager()

# Request Models
class OrderRequest(BaseModel):
    customer_id: str
    details: Optional[Dict] = None

class StatusResponse(BaseModel):
    status: str
    active_connections: int
    service: str = "frontend_service"

# Message Handlers
@monitor_message_processing('frontend_service')
async def handle_order_update(message: dict):
    """Handle updates from various services and forward to WebSocket"""
    try:
        order_id = message.get("order_id")
        if not order_id:
            raise ServiceException(message="Missing order_id in message", details=message)

        await manager.send_update(order_id, message)
        
    except Exception as e:
        logger.error("order_update_failed", error=str(e), message=message)

def message_handler(ch, method, properties, body):
    try:
        if isinstance(body, bytes):
            message = json.loads(body.decode('utf-8'))
        else:
            message = json.loads(body)

        asyncio.run(handle_order_update(message))
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error("message_processing_failed", error=str(e))
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

# Setup consumers for all update queues
update_queues = ["order_supplied", "doener_supplied", "invoice_supplied"]
for queue in update_queues:
    mq.consume(queue, message_handler)

# WebSocket endpoint
@app.websocket("/ws/{order_id}")
async def websocket_endpoint(websocket: WebSocket, order_id: str):
    await manager.connect(order_id, websocket)
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            logger.debug("websocket_message_received", order_id=order_id, data=data)
    except WebSocketDisconnect:
        manager.disconnect(order_id)
    except Exception as e:
        logger.error("websocket_error", order_id=order_id, error=str(e))
        manager.disconnect(order_id)

# HTTP endpoints
@app.post("/order/doener")
@monitor_message_processing('frontend_service')
async def create_order(order: OrderRequest):
    try:
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
        
        # Publish to required services
        mq.publish("doener_requests", message.to_json())
        mq.publish("order_requests", message.to_json())
        
        logger.info("order_created", 
                   order_id=order_id, 
                   customer_id=order.customer_id)
        
        return {
            "order_id": order_id,
            "correlation_id": correlation_id,
            "websocket_url": f"/ws/{order_id}",
            "status": "created"
        }
        
    except Exception as e:
        logger.error("create_order_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to create order", "error": str(e)}
        )

@app.get("/status")
async def get_status():
    return StatusResponse(
        status="healthy",
        active_connections=len(manager.active_connections)
    )

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    logger.info("frontend_service_starting")

@app.on_event("shutdown")
async def shutdown_event():
    # Close all WebSocket connections
    for order_id in list(manager.active_connections.keys()):
        manager.disconnect(order_id)
    logger.info("frontend_service_shutting_down")