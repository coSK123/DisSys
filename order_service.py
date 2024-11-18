from fastapi import FastAPI, HTTPException
from common.message_queue import RabbitMQ
from common.types import Message, ServiceException, OrderStatus
from common.monitoring import setup_monitoring, monitor_message_processing
import json
from datetime import datetime
import structlog
import asyncio
from typing import Dict, Optional
import threading

app = FastAPI()
logger = setup_monitoring(app, 'order_service')

# Initialize mq as None and set it in startup
mq = None

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

def run_consumer(mq_instance):
    """Run the consumer in a separate thread"""
    try:
        logger.info("Starting consumer thread")
        mq_instance.start_consuming()
    except Exception as e:
        logger.error("Consumer thread error", error=str(e))

@monitor_message_processing('order_service')
async def handle_order_request(message: Dict) -> None:
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
        mq.publish("order_supplied", response.to_json())
        
    except Exception as e:
        error_response = Message(
            correlation_id=message["correlation_id"],
            order_id=message["order_id"],
            timestamp=datetime.now(),
            message_type="ORDER_CREATION_FAILED",
            payload={"status": OrderStatus.FAILED.value},
            error={"message": str(e), "type": type(e).__name__}
        )
        mq.publish("order_supplied", error_response.to_json())
        raise

@monitor_message_processing('order_service')
async def handle_doener_supplied(message: Dict) -> None:
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
                   
        mq.publish("invoice_requests", invoice_request.to_json())
        
    except Exception as e:
        logger.error("doener_update_failed",
                    error=str(e),
                    order_id=message["order_id"])
        raise

def message_handler(ch, method, properties, body):
    try:
        if isinstance(body, bytes):
            message = json.loads(body.decode('utf-8'))
        else:
            message = json.loads(body)

        if method.routing_key == 'order_requests':
            asyncio.run(handle_order_request(message))
        elif method.routing_key == 'doener_supplied':
            asyncio.run(handle_doener_supplied(message))

        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error("message_processing_failed",
                    error=str(e),
                    body=body)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

@app.on_event("startup")
async def startup_event():
    global mq
    logger.info("Starting order service...")
    try:
        mq = RabbitMQ()
        
        # Set up consumers
        mq.consume('order_requests', message_handler)
        mq.consume('doener_supplied', message_handler)
        
        # Start consumer in a separate thread
        consumer_thread = threading.Thread(target=run_consumer, args=(mq,), daemon=True)
        consumer_thread.start()
        
        logger.info("Order service startup completed successfully")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    global mq
    if mq:
        mq.close()
    logger.info("Order service shutdown complete")

@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "order_service"}