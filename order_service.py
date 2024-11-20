from fastapi import FastAPI, Depends, HTTPException
from common.types import Message, ServiceException, OrderStatus
from common.monitoring import monitor_message_processing
from common.mq_service import RabbitMQService
from common.config import Config
import json
from datetime import datetime
import structlog
from typing import Dict, Optional

# Initialize FastAPI app
app = FastAPI(title="Order Service")
logger = structlog.get_logger()


# Configuration
class OrderServiceSettings:
    rabbitmq_url: str = Config.get_rabbitmq_url()
    queues_to_verify: list[str] = Config.QUEUES
    order_queue: str = "order_requests"
    order_response_queue: str = "order_supplied"
    invoice_queue: str = "invoice_requests"
    doener_response_queue: str = "doener_supplied"


settings = OrderServiceSettings()


# Order Database
class OrderDatabase:
    def __init__(self):
        self.orders: Dict[str, Dict] = {}

    async def create_order(self, order_id: str, data: dict) -> None:
        self.orders[order_id] = {
            "created_at": datetime.now().isoformat(),
            "status": OrderStatus.CREATED.value,
            "updates": [],
            **data
        }
        logger.info("order_created", order_id=order_id)

    async def update_order(self, order_id: str, data: dict) -> None:
        if order_id not in self.orders:
            raise ServiceException(
                message="Order not found",
                details={"order_id": order_id}
            )

        self.orders[order_id].update(data)
        self.orders[order_id]["updates"].append({
            "timestamp": datetime.now().isoformat(),
            "data": data
        })
        logger.info("order_updated", order_id=order_id, updates=data)

    async def get_order(self, order_id: str) -> Optional[Dict]:
        return self.orders.get(order_id)


db = OrderDatabase()


# Dependency for RabbitMQ
def get_rabbitmq_service() -> RabbitMQService:
    mq = app.state.rabbitmq_service
    if not mq or not mq.connection:
        raise HTTPException(status_code=503, detail="Message queue service unavailable")
    return mq


@monitor_message_processing('order_service')
async def handle_order_request(message: Dict, mq_service: RabbitMQService):
    """Process incoming order requests."""
    try:
        await db.create_order(message["order_id"], message.get("payload", {}))

        response = Message(
            correlation_id=message["correlation_id"],
            order_id=message["order_id"],
            timestamp=datetime.now(),
            message_type="ORDER_ACKNOWLEDGED",
            payload={"status": OrderStatus.PROCESSING.value}
        )

        logger.info("order_acknowledged", order_id=message["order_id"])
        await mq_service.publish(settings.order_response_queue, response.to_json())

    except Exception as e:
        error_response = Message(
            correlation_id=message["correlation_id"],
            order_id=message["order_id"],
            timestamp=datetime.now(),
            message_type="ORDER_CREATION_FAILED",
            payload={"status": OrderStatus.FAILED.value},
            error={"message": str(e), "type": type(e).__name__}
        )
        await mq_service.publish(settings.order_response_queue, error_response.to_json())
        raise


@monitor_message_processing('order_service')
async def handle_doener_supplied(message: Dict, mq_service: RabbitMQService):
    """Process incoming döner assignment responses."""
    try:
        await db.update_order(message["order_id"], {
            "doener_shop": message["payload"]["shop"],
            "price": message["payload"]["price"],
            "status": message["payload"]["status"]
        })

        invoice_request = Message(
            correlation_id=message["correlation_id"],
            order_id=message["order_id"],
            timestamp=datetime.now(),
            message_type="INVOICE_REQUESTED",
            payload={
                "price": message["payload"]["price"],
                "shop": message["payload"]["shop"]
            }
        )

        logger.info("requesting_invoice",
                    order_id=message["order_id"],
                    shop_id=message["payload"]["shop"]["id"])

        await mq_service.publish(settings.invoice_queue, invoice_request.to_json())

    except Exception as e:
        logger.error("doener_update_failed",
                     error=str(e),
                     order_id=message["order_id"])
        raise


async def message_handler(message):
    """Handle RabbitMQ messages."""
    try:
        message_body = json.loads(message.body.decode("utf-8"))

        if message.routing_key == settings.order_queue:
            await handle_order_request(message_body, app.state.rabbitmq_service)
        elif message.routing_key == settings.doener_response_queue:
            await handle_doener_supplied(message_body, app.state.rabbitmq_service)

        await message.ack()
    except Exception as e:
        logger.error("message_processing_failed", error=str(e), message=message.body)
        raise


@app.on_event("startup")
async def startup_event():
    """Startup event for initializing RabbitMQ and consuming messages."""
    logger.info("Starting Order Service...")

    mq_service = RabbitMQService(settings.rabbitmq_url)
    await mq_service.initialize()

    app.state.rabbitmq_service = mq_service

    await mq_service.verify_queues(settings.queues_to_verify)
    await mq_service.consume(settings.order_queue, message_handler)
    await mq_service.consume(settings.doener_response_queue, message_handler)

    logger.info("Order Service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event to clean up resources."""
    mq_service = app.state.rabbitmq_service
    if mq_service:
        await mq_service.close()
    logger.info("Order Service shutdown completed")


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get order details by ID."""
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/health")
async def health_check(mq_service: RabbitMQService = Depends(get_rabbitmq_service)):
    """Health check endpoint."""
    rabbitmq_status = "connected" if mq_service.connection and mq_service.connection.connected else "disconnected"
    return {"status": "healthy", "service": "order_service", "rabbitmq_status": rabbitmq_status}