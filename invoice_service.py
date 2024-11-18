from fastapi import FastAPI
from common.message_queue import RabbitMQ
from common.types import Message, ServiceException, OrderStatus
from common.monitoring import setup_monitoring, monitor_message_processing
import json
from datetime import datetime
import structlog
import asyncio
import threading

app = FastAPI()
logger = setup_monitoring(app, 'invoice_service')

# Initialize mq as None and set it in startup
mq = None

def run_consumer(mq_instance):
    """Run the consumer in a separate thread"""
    try:
        logger.info("Starting consumer thread")
        mq_instance.start_consuming()
    except Exception as e:
        logger.error("Consumer thread error", error=str(e))

@monitor_message_processing('invoice_service')
async def create_invoice(message: dict) -> None:
    try:
        logger.info("creating_invoice",
                   order_id=message["order_id"])
        
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
                   
        mq.publish("invoice_supplied", response.to_json())
        
    except Exception as e:
        error_response = Message(
            correlation_id=message["correlation_id"],
            order_id=message["order_id"],
            timestamp=datetime.now(),
            message_type="INVOICE_CREATION_FAILED",
            payload={"status": OrderStatus.FAILED.value},
            error={"message": str(e), "type": type(e).__name__}
        )
        mq.publish("invoice_supplied", error_response.to_json())
        raise

def message_handler(ch, method, properties, body):
    try:
        if isinstance(body, bytes):
            message = json.loads(body.decode('utf-8'))
        else:
            message = json.loads(body)

        asyncio.run(create_invoice(message))
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error("message_processing_failed",
                    error=str(e),
                    body=body)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

@app.on_event("startup")
async def startup_event():
    global mq
    logger.info("Starting invoice service...")
    try:
        mq = RabbitMQ()
        
        # Set up consumer
        mq.consume("invoice_requests", message_handler)
        
        # Start consumer in a separate thread
        consumer_thread = threading.Thread(target=run_consumer, args=(mq,), daemon=True)
        consumer_thread.start()
        
        logger.info("Invoice service startup completed successfully")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    global mq
    if mq:
        mq.close()
    logger.info("Invoice service shutdown complete")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "invoice_service"}