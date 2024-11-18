from fastapi import FastAPI
from common.message_queue import RabbitMQ
from common.types import Message, ServiceException, OrderStatus
from common.monitoring import setup_monitoring, monitor_message_processing
import json
import random
import asyncio
from datetime import datetime
from typing import Dict
import structlog
import threading

app = FastAPI()
logger = setup_monitoring(app, 'doener_service')

# Initialize mq as None and set it in startup
mq = None

class DoenerShopFinder:
    def __init__(self):
        self.shops = [
            {"id": "shop1", "name": "Best Döner", "price": 8.50},
            {"id": "shop2", "name": "King Döner", "price": 7.50},
            {"id": "shop3", "name": "Döner Palace", "price": 9.00}
        ]

    async def find_available_shop(self, message: Dict) -> Dict:
        try:
            await asyncio.sleep(0.5)  # simulating http call time
            shop = random.choice(self.shops)
            
            if not shop:
                raise ServiceException(
                    message="No available shops found",
                    details={"order_id": message["order_id"]}
                )
                
            return shop
        except Exception as e:
            logger.error("shop_finder_error",
                        error=str(e),
                        order_id=message["order_id"])
            raise

shop_finder = DoenerShopFinder()

def run_consumer(mq_instance):
    """Run the consumer in a separate thread"""
    try:
        logger.info("Starting consumer thread")
        mq_instance.start_consuming()
    except Exception as e:
        logger.error("Consumer thread error", error=str(e))

@monitor_message_processing('doener_service')
async def handle_doener_request(message: Dict) -> None:
    try:
        logger.info("processing_doener_request",
                   order_id=message["order_id"])
        
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

        logger.info("doener_assigned",
                   order_id=message["order_id"],
                   shop_id=shop["id"])
                   
        mq.publish("doener_supplied", response.to_json())
        
    except Exception as e:
        error_response = Message(
            correlation_id=message["correlation_id"],
            order_id=message["order_id"],
            timestamp=datetime.now(),
            message_type="DOENER_ASSIGNMENT_FAILED",
            payload={"status": OrderStatus.FAILED.value},
            error={"message": str(e), "type": type(e).__name__}
        )
        mq.publish("doener_supplied", error_response.to_json())
        raise

def message_handler(ch, method, properties, body):
    try:
        if isinstance(body, bytes):
            message = json.loads(body.decode('utf-8'))
        else:
            message = json.loads(body)

        asyncio.run(handle_doener_request(message))
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error("message_processing_failed",
                    error=str(e),
                    body=body)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

@app.on_event("startup")
async def startup_event():
    global mq
    logger.info("Starting doener service...")
    try:
        mq = RabbitMQ()
        
        # Set up consumer
        mq.consume('doener_requests', message_handler)
        
        # Start consumer in a separate thread
        consumer_thread = threading.Thread(target=run_consumer, args=(mq,), daemon=True)
        consumer_thread.start()
        
        logger.info("Doener service startup completed successfully")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    global mq
    if mq:
        mq.close()
    logger.info("Doener service shutdown complete")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "doener_service"}