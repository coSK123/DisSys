from fastapi import FastAPI
from common.message_queue import RabbitMQ
import json
import random
from dataclasses import asdict, dataclass
from typing import Dict, Any
import asyncio
from datetime import datetime

@dataclass
class Message:
    correlation_id: str
    order_id: str
    timestamp: datetime
    message_type: str
    payload: Dict[str, Any]
    version: str = "1.0"

    def to_json(self):
        dict_repr = asdict(self)
        dict_repr['timestamp'] = self.timestamp.isoformat()
        return dict_repr

mq = RabbitMQ()

class DoenerShopFinder:
    async def find_available_shop(self, message, callback):
        await asyncio.sleep(0.5)  # simulating http call time

        # Simulated shop finding logic
        shops = [
            {"id": "shop1", "name": "Best Döner", "price": 8.50},
            {"id": "shop2", "name": "King Döner", "price": 7.50},
            {"id": "shop3", "name": "Döner Palace", "price": 9.00}
        ]
        shop = random.choice(shops)
        callback(message, shop)

shop_finder = DoenerShopFinder()

def handle_doener_supplied(message, shop):
    response = Message(
        correlation_id=message["correlation_id"],
        order_id=message["order_id"],
        timestamp=datetime.now(),
        message_type="DOENER_ASSIGNED",
        payload={
            "shop": shop,
            "price": shop["price"],
            "status": "FOUND"
        }
    )

    print(f"Found shop for order {message['order_id']}: {shop['name']}")
    mq.publish("doener_supplied", response.to_json())

def handle_doener_request(ch, method, properties, body):
    try:
        if isinstance(body, bytes):
            message = json.loads(body.decode('utf-8'))
        else:
            message = json.loads(body)

        asyncio.run(shop_finder.find_available_shop(message, handle_doener_supplied))
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except json.JSONDecodeError as e:
        print(f"Error decoding message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        print(f"Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

# Start consuming doener preparation requests
mq.consume('doener_requests', handle_doener_request)