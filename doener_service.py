from fastapi import FastAPI, Depends, HTTPException
from prometheus_client import make_asgi_app

from common.types import Message, ServiceException, OrderStatus
from common.monitoring import monitor_message_processing
from common.mq_service import RabbitMQService
from common.config import Config
import json
import random
import asyncio
from datetime import datetime
from typing import Dict
import structlog

# Initialize FastAPI app
app = FastAPI(title="Döner Assignment Service")
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
logger = structlog.get_logger()

# Configuration
class DoenerServiceSettings:
    rabbitmq_url: str = Config.get_rabbitmq_url()
    service_name: str = "doener_service"
    update_queue: str = "doener_requests"
    response_queue: str = "doener_supplied"

settings = DoenerServiceSettings()

# Shop Finder
class DoenerShopFinder:
    def __init__(self):
        self.shops = [
            {"id": "shop1", "name": "Best Döner", "price": 8.50},
            {"id": "shop2", "name": "King Döner", "price": 7.50},
            {"id": "shop3", "name": "Döner Palace", "price": 9.00}
        ]

    async def find_available_shop(self, message: Dict) -> Dict:
        """Simulate finding an available shop."""
        try:

            await asyncio.sleep(1.5) # HTTP latency simulated
            shop = random.choice(self.shops)
            if not shop:
                raise ServiceException(
                    message="No available shops found",
                    details={"order_id": message["order_id"]}
                )
            return shop
        except Exception as e:
            logger.error("shop_finder_error", error=str(e), order_id=message["order_id"])
            raise

shop_finder = DoenerShopFinder()

# Dependency for RabbitMQ
def get_rabbitmq_service() -> RabbitMQService:
    mq = app.state.rabbitmq_service
    if not mq or not mq.connection:  # Ensure RabbitMQ connection is active
        raise HTTPException(status_code=503, detail="Message queue service unavailable")
    return mq

@monitor_message_processing('doener_service')
async def handle_doener_request(message: Dict, mq_service: RabbitMQService):
    """Process incoming döner requests."""
    try:
        logger.info("processing_doener_request", order_id=message["order_id"])
        shop = await shop_finder.find_available_shop(message)
        
        response = Message(
            correlation_id=message["correlation_id"],
            order_id=message["order_id"],
            timestamp=datetime.now(),
            message_type="DOENER_ASSIGNED",
            payload={
                "shop": shop,
                "price": shop["price"],
                "status": OrderStatus.DOENER_ASSIGNED.value
            }
        )
        
        logger.info("doener_assigned", order_id=message["order_id"], shop_id=shop["id"])
        await mq_service.publish(settings.response_queue, response.to_json())

    except Exception as e:
        error_response = Message(
            correlation_id=message["correlation_id"],
            order_id=message["order_id"],
            timestamp=datetime.now(),
            message_type="DOENER_ASSIGNMENT_FAILED",
            payload={"status": OrderStatus.FAILED.value},
            error={"message": str(e), "type": type(e).__name__}
        )
        await mq_service.publish(settings.response_queue, error_response.to_json())
        logger.error("doener_request_failed", error=str(e), order_id=message.get("order_id"))
        raise

async def message_handler(message):
    """Handle RabbitMQ messages."""
    try:
        message_body = json.loads(message.body.decode("utf-8"))
        await handle_doener_request(message_body, app.state.rabbitmq_service)
        await message.ack()
    except Exception as e:
        logger.error("message_processing_failed", error=str(e), message=message.body)
        await message.nack(requeue=True)
        raise

@app.on_event("startup")
async def startup_event():
    """Startup event for initializing RabbitMQ and consuming messages."""
    logger.info("Starting Döner Assignment Service...")
    
    mq_service = RabbitMQService(settings.service_name, settings.rabbitmq_url)
    await mq_service.initialize()
    
    app.state.rabbitmq_service = mq_service

    await mq_service.consume(settings.update_queue, message_handler)
    
    logger.info("Döner Assignment Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event to clean up resources."""
    mq_service = app.state.rabbitmq_service
    if mq_service:
        await mq_service.close()
    logger.info("Döner Assignment Service shutdown completed")

@app.get("/health")
async def health_check(mq_service: RabbitMQService = Depends(get_rabbitmq_service)):
    """Health check endpoint."""
    rabbitmq_status = "connected" if mq_service.connection and mq_service.connection.connected else "disconnected"
    return {"status": "healthy", "rabbitmq_status": rabbitmq_status}
