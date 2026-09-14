from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class EventType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    TRANSFER = "TRANSFER"
    REVERSAL = "REVERSAL"
    FEE = "FEE"

class AuditStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    REJECTED = "REJECTED"
    REVERSED = "REVERSED"
    PENDING = "PENDING"

class Event(BaseModel):
    event_id: str
    account_id: str
    timestamp: datetime
    type: EventType
    amount: float
    currency: str = "PKR"
    target_account_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AuditLogEntry(BaseModel):
    event_id: str
    status: AuditStatus
    reason: Optional[str] = None
    processed_at: datetime = Field(default_factory=datetime.utcnow)