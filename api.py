from typing import List
from fastapi import APIRouter, HTTPException
from ledger import LedgerEngine
from models import AuditLogEntry, Event

router = APIRouter()
engine = LedgerEngine()

@router.post("/events", response_model=AuditLogEntry)
def ingest_event(event: Event):
    return engine.ingest(event)

@router.post("/events/batch", response_model=List[AuditLogEntry])
def ingest_batch_events(events: List[Event]):
    return engine.ingest_batch(events)

@router.get("/accounts/{account_id}/balance")
def get_account_balance(account_id: str):
    balance = engine.get_balance(account_id)
    return {"account_id": account_id, "balance": balance}

@router.get("/accounts/{account_id}/transactions", response_model=List[Event])
def get_account_transactions(account_id: str):
    transactions = engine.get_transactions(account_id)
    return transactions

@router.post("/snapshot")
def create_snapshot():
    return engine.snapshot()

@router.post("/restore")
def restore_engine(snapshot_data: dict):
    try:
        engine.restore(snapshot_data)
        return {"status": "success", "message": "Engine successfully restored from snapshot"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))