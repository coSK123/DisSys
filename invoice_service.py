from fastapi import FastAPI, Depends, HTTPException
from common.types import Message, ServiceException, OrderStatus
from common.monitoring import monitor_message_processing
from common.mq_service import RabbitMQService
from common.config import Config
import json
from datetime import datetime
import structlog

# Initialize FastAPI app
app = FastAPI(title="Invoice Service")
logger = structlog.get_logger()


# Configuration
class InvoiceServiceSettings:
    rabbitmq_url: str = Config.get_rabbitmq_url()
    queues_to_verify: list[str] = Config.QUEUES
    invoice_queue: str = "invoice_requests"
    response_queue: str = "invoice_supplied"


settings = InvoiceServiceSettings()


# Dependency for RabbitMQ
def get_rabbitmq_service() -> RabbitMQService:
    mq = app.state.rabbitmq_service
    if not mq or not mq.connection:
        raise HTTPException(status_code=503, detail="Message queue service unavailable")
    return mq


@monitor_message_processing('invoice_service')
async def create_invoice(message: dict, mq_service: RabbitMQService) -> None:
    """Process invoice creation requests."""
    try:
        logger.info("creating_invoice", order_id=message["order_id"])

        if "payload" not in message or "price" not in message["payload"]:
            raise ServiceException(
                message="Invalid message format",
                details={"order_id": message["order_id"]}
            )

        response = Message(
            correlation_id=message["correlation_id"],
            order_id=message["order_id"],
            timestamp=datetime.now(),
            message_type="INVOICE_CREATED",
            payload={
                "invoice_id": f"INV-{message['order_id'][:8]}",
                "total": message["payload"]["price"] + 1.50,  # Add delivery fee
                "status": OrderStatus.INVOICED.value
            }
        )

        logger.info("invoice_created",
                    order_id=message["order_id"],
                    invoice_id=response.payload["invoice_id"])

        await mq_service.publish(settings.response_queue, response.to_json())

    except Exception as e:
        error_response = Message(
            correlation_id=message["correlation_id"],
            order_id=message["order_id"],
            timestamp=datetime.now(),
            message_type="INVOICE_CREATION_FAILED",
            payload={"status": OrderStatus.FAILED.value},
            error={"message": str(e), "type": type(e).__name__}
        )
        await mq_service.publish(settings.response_queue, error_response.to_json())
        raise


async def message_handler(message):
    """Handle RabbitMQ messages."""
    try:
        message_body = json.loads(message.body.decode("utf-8"))
        await create_invoice(message_body, app.state.rabbitmq_service)
        await message.ack()
    except Exception as e:
        logger.error("message_processing_failed", error=str(e), message=message.body)
        raise


@app.on_event("startup")
async def startup_event():
    """Startup event for initializing RabbitMQ and consuming messages."""
    logger.info("Starting Invoice Service...")

    mq_service = RabbitMQService(settings.rabbitmq_url)
    await mq_service.initialize()

    app.state.rabbitmq_service = mq_service

    await mq_service.verify_queues(settings.queues_to_verify)
    await mq_service.consume(settings.invoice_queue, message_handler)

    logger.info("Invoice Service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event to clean up resources."""
    mq_service = app.state.rabbitmq_service
    if mq_service:
        await mq_service.close()
    logger.info("Invoice Service shutdown completed")


@app.get("/health")
async def health_check(mq_service: RabbitMQService = Depends(get_rabbitmq_service)):
    """Health check endpoint."""
    rabbitmq_status = "connected" if mq_service.connection and mq_service.connection.connected else "disconnected"
    return {"status": "healthy", "service": "invoice_service", "rabbitmq_status": rabbitmq_status}