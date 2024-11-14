from fastapi import FastAPI
from common.message_queue import RabbitMQ
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Any

mq = RabbitMQ()

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
        # Convert datetime to string
        dict_repr['timestamp'] = self.timestamp.isoformat()
        return dict_repr

class OrderDatabase:
    def __init__(self):
        self.orders = {}

    def create_order(self, order_id: str, data: dict):
        self.orders[order_id] = {
            "created_at": datetime.now().isoformat(),  # Store as ISO string
            "status": "CREATED",
            **data
        }

    def update_order(self, order_id: str, data: dict):
        if order_id in self.orders:
            self.orders[order_id].update(data)

db = OrderDatabase()

def handle_order_request(ch, method, properties, body):
    try:
        # Handle both dict and bytes/string inputs
        if isinstance(body, (bytes, str)):
            if isinstance(body, bytes):
                message_str = body.decode('utf-8')
            else:
                message_str = body
            message = json.loads(message_str)
        else:
            message = body  # Already a dict

        # Create order in database
        db.create_order(message["order_id"], message.get("payload", {}))
        
        # Acknowledge order creation
        response = Message(
            correlation_id=message["correlation_id"],
            order_id=message["order_id"],
            timestamp=datetime.now(),
            message_type="ORDER_ACKNOWLEDGED",
            payload={"status": "PROCESSING"}
        )

        print(f"Order {message['order_id']} acknowledged")
        
        # Publish response
        mq.publish("order_supplied", response.to_json())
        
    except json.JSONDecodeError as e:
        print(f"Error decoding message: {e}")
        raise
        
    except KeyError as e:
        print(f"Missing required field in message: {e}")
        raise
        
    except Exception as e:
        print(f"Error handling order request: {e}")
        raise


def handle_doener_supplied(ch, method, properties, body):
    message = json.loads(body)
    db.update_order(message["order_id"], {
        "doener_shop": message["payload"]["shop"],
        "price": message["payload"]["price"],
        "status": "DOENER_ASSIGNED"
    })
    
    # Request invoice
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

    print(f"Order {message['order_id']} assigned to {message['payload']['shop']} - requesting invoice")
    mq.publish("invoice_requests", invoice_request.to_json())

# Start consuming order requests
mq.consume('order_requests', handle_order_request)
mq.consume('doener_supplied', handle_doener_supplied)