from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
import json

class OrderStatus(str, Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    READY = "ready"
    DELIVERED = "delivered"

class Order(BaseModel):
    id: str
    items: List[str]
    total_price: float
    status: OrderStatus = OrderStatus.PENDING
