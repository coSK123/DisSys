from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

class OrderStatus(Enum):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    DOENER_ASSIGNED = "DOENER_ASSIGNED"
    INVOICED = "INVOICED"
    FAILED = "FAILED"

@dataclass
class Message:
    correlation_id: str
    order_id: str
    timestamp: datetime
    message_type: str
    payload: Dict[str, Any]
    version: str = "1.0"
    error: Optional[Dict[str, Any]] = None

    def to_json(self):
        dict_repr = asdict(self)
        dict_repr['timestamp'] = self.timestamp.isoformat()
        return dict_repr

@dataclass
class ServiceException(Exception):
    message: str
    details: Dict[str, Any]
    status_code: int = 500