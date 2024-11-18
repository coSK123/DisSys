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
import logging

# Initialize FastAPI app
app = FastAPI(title="Döner Order System")

# Global variable to track initialization
mq = None

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

struct_logger = structlog.get_logger()

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

@app.on_event("startup")
async def startup_event():
    """
    FastAPI startup event handler
    """
    global mq
    logger.info("Starting Frontend Service...")
    
    try:
        mq = RabbitMQ()
        logger.info("RabbitMQ connection initialized")
        
        # Verify queues
        queues_to_verify = ["doener_requests", "order_requests", "order_supplied", "doener_supplied", "invoice_supplied"]
        for queue_name in queues_to_verify:
            try:
                mq._channel.queue_declare(queue=queue_name, passive=True)
                logger.info(f"Queue verified: {queue_name}")
            except Exception as e:
                logger.error(f"Failed to verify queue {queue_name}: {str(e)}")
                raise
        
        # Setup consumers for all update queues
        update_queues = ["order_supplied", "doener_supplied", "invoice_supplied"]
        for queue in update_queues:
            mq.consume(queue, message_handler)
            logger.info(f"Consumer set up for queue: {queue}")
            
        logger.info("Frontend Service startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

@app.post("/order/doener")
async def create_order(order: OrderRequest):
    """Create a new döner order"""
    logger.info(f"Received order request for customer: {order.customer_id}")
    
    try:
        if not mq or not mq._connection or mq._connection.is_closed:
            logger.error("RabbitMQ connection not available")
            raise HTTPException(
                status_code=503,
                detail="Message queue service unavailable"
            )
        
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
        logger.debug(f"Prepared message: {message_json}")
        
        doener_success = mq.publish("doener_requests", message_json)
        order_success = mq.publish("order_requests", message_json)
        
        if not doener_success or not order_success:
            logger.error(f"Failed to publish messages. Doener: {doener_success}, Order: {order_success}")
            raise HTTPException(
                status_code=500,
                detail="Failed to process order"
            )
            
        logger.info(f"Order created successfully. Order ID: {order_id}")
        
        return {
            "order_id": order_id,
            "correlation_id": correlation_id,
            "websocket_url": f"/ws/{order_id}",
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to create order", "error": str(e)}
        )

@app.get("/status")
async def get_status():
    """Get service status"""
    try:
        if not mq:
            return {
                "status": "unhealthy",
                "rabbitmq_status": "not_initialized",
                "service": "frontend_service"
            }
            
        mq._ensure_connection()
        rabbitmq_status = "connected" if mq._connection and mq._connection.is_open else "disconnected"
        
        return {
            "status": "healthy",
            "rabbitmq_status": rabbitmq_status,
            "service": "frontend_service",
            "queues": ["doener_requests", "order_requests", "order_supplied", "doener_supplied", "invoice_supplied"]
        }
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"message": "Service unhealthy", "error": str(e)}
        )

@app.websocket("/ws/{order_id}")
async def websocket_endpoint(websocket: WebSocket, order_id: str):
    await manager.connect(order_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("websocket_message_received", order_id=order_id, data=data)
    except WebSocketDisconnect:
        manager.disconnect(order_id)
    except Exception as e:
        logger.error("websocket_error", order_id=order_id, error=str(e))
        manager.disconnect(order_id)

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Shutting down Frontend Service...")
    if mq:
        mq.close()
    for order_id in list(manager.active_connections.keys()):
        manager.disconnect(order_id)
    logger.info("Frontend Service shutdown complete")