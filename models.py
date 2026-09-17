from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class EventType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    TRANSFER = "TRANSFER"
    REVERSAL = "REVERSAL"

class Event(BaseModel):
    event_id: str = Field(..., description="Unique idempotency key for the transaction", example="evt_101")
    type: EventType = Field(..., description="Type of financial operation", example="DEPOSIT")
    account_id: str = Field(..., description="Primary account identifier", example="acc_001")
    amount: float = Field(..., gt=0, description="Transaction amount (must be greater than 0)", example=500.0)
    target_account_id: Optional[str] = Field(None, description="Destination account ID (required only for TRANSFER)", example="acc_002")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_101",
                "type": "DEPOSIT",
                "account_id": "acc_001",
                "amount": 500.0,
                "target_account_id": None
            }
        }

class AuditLogEntry(BaseModel):
    event_id: str = Field(..., example="evt_101")
    status: str = Field(..., example="SUCCESS")
    message: str = Field(..., example="Successfully processed DEPOSIT of 500.0 for account acc_001")
    balance_after: float = Field(..., example=1500.0)