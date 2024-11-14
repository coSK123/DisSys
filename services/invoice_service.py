from fastapi import FastAPI
from common.message_queue import RabbitMQ
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Any

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

def create_invoice(ch, method, properties, body):
    try:
        if isinstance(body, bytes):
            message = json.loads(body.decode('utf-8'))
        else:
            message = json.loads(body)

        # Create invoice response
        response = Message(
            correlation_id=message["correlation_id"],
            order_id=message["order_id"],
            timestamp=datetime.now(),
            message_type="INVOICE_CREATED",
            payload={
                "invoice_id": f"INV-{message['order_id'][:8]}",
                "total": message["payload"]["price"] + 1.50,  # Add delivery fee
                "status": "INVOICED"
            }
        )
        
        print(f"Created invoice for order {message['order_id']}")
        mq.publish("invoice_supplied", response.to_json())
        
    except json.JSONDecodeError as e:
        print(f"Error decoding message: {e}")
    except Exception as e:
        print(f"Error processing invoice: {e}")

# Start consuming invoice requests
mq.consume("invoice_requests", create_invoice)