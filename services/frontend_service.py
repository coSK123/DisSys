from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from common.message_queue import RabbitMQ
import json
import asyncio
from typing import Dict
import uuid
from datetime import datetime
import threading
from dataclasses import dataclass, asdict
from typing import Any


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


app = FastAPI()
mq = RabbitMQ()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, order_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[order_id] = websocket
        
    def disconnect(self, order_id: str):
        if order_id in self.active_connections:
            del self.active_connections[order_id]
            
    async def send_update(self, order_id: str, message: dict):
        if order_id in self.active_connections:
            try:
                await self.active_connections[order_id].send_json(message)
            except Exception as e:
                print(f"Error sending message to {order_id}: {e}")
                self.disconnect(order_id)

manager = ConnectionManager()

@dataclass
class OrderUpdate:
    order_id: str
    correlation_id: str
    status: str
    details: dict
    timestamp: datetime = datetime.now()

    def to_json(self):
        dict_repr = asdict(self)
        dict_repr['timestamp'] = self.timestamp.isoformat()
        return dict_repr

# Queue message handlers
async def handle_order_supplied(message: dict):
    order_id = message["order_id"]
    update = OrderUpdate(
        order_id=order_id,
        correlation_id=message["correlation_id"],
        status="ORDER_CREATED",
        details={"message": "Order has been created and is being processed"}
    )
    print(f"Order {order_id} has been created")
    await manager.send_update(order_id, update.to_json())

async def handle_doener_supplied(message: dict):
    order_id = message["order_id"]
    update = OrderUpdate(
        order_id=order_id,
        correlation_id=message["correlation_id"],
        status="DOENER_ASSIGNED",
        details={
            "shop": message["payload"]["shop"],
            "price": message["payload"]["price"]
        }
    )
    print(f"Order {order_id} has been assigned to {message['payload']['shop']['name']}")
    await manager.send_update(order_id, update.to_json())

async def handle_invoice_supplied(message: dict):
    order_id = message["order_id"]
    update = OrderUpdate(
        order_id=order_id,
        correlation_id=message["correlation_id"],
        status="INVOICE_READY",
        details={
            "invoice_id": message["payload"].get("invoice_id"),
            "total": message["payload"].get("total"),
            "status": "ready_for_payment"
        }
    )
    print(f"Order {order_id} is ready for payment")
    await manager.send_update(order_id, update.to_json())

# Message queue consumer that dispatches to WebSocket
async def process_queue_message(queue_name: str, message: dict):
    handlers = {
        "order_supplied": handle_order_supplied,
        "doener_supplied": handle_doener_supplied,
        "invoice_supplied": handle_invoice_supplied
    }
    
    if queue_name in handlers:
        await handlers[queue_name](message)

def setup_queue_consumer():
    def callback(ch, method, properties, body):
        try:

            print(f"Received message: {body}")

            message = json.loads(body)
            queue_name = method.routing_key
            
            # Create new event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(process_queue_message(queue_name, message))
            except Exception as e:
                print(f"Error processing message: {e}")
            finally:
                loop.close()
        except json.JSONDecodeError as e:
            print(f"Error decoding message: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    queues = ["order_supplied", "doener_supplied", "invoice_supplied"]
    mq.setup_consumers(queues, callback)

@app.on_event("startup")
async def startup_event():
    thread = threading.Thread(target=setup_queue_consumer, daemon=True)
    thread.start()

@app.websocket("/ws/{order_id}")
async def websocket_endpoint(websocket: WebSocket, order_id: str):
    await manager.connect(order_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(order_id)

class Order(BaseModel):
    customer_id: str

@app.post("/order/doener")
async def create_order(order: Order):
    order_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    
    # Create initial message using Message class
    message = Message(
        correlation_id=correlation_id,
        order_id=order_id,
        timestamp=datetime.now(),
        message_type="ORDER_CREATED",
        payload={
            "customer_id": order.customer_id,
            "status": "CREATED"
        }
    )
    
    # Publish to initial queues
    mq.publish("doener_requests", message.to_json())
    mq.publish("order_requests", message.to_json())
    
    return {
        "order_id": order_id,
        "correlation_id": correlation_id,
        "websocket_url": f"/ws/{order_id}"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "active_connections": len(manager.active_connections)}