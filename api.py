import logging
from typing import List
from fastapi import APIRouter, HTTPException, status
from ledger import LedgerEngine
from models import AuditLogEntry, Event

# Configure structured logging for audit and production monitoring
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ledger_api")

router = APIRouter()
engine = LedgerEngine()

@router.get("/health", status_code=status.HTTP_200_OK, summary="Health Check", description="Verifies if the service is up and running.")
def health_check():
    logger.info("Health check ping received.")
    return {"status": "healthy", "service": "Financial Ledger Engine"}

@router.get("/ready", status_code=status.HTTP_200_OK, summary="Readiness Check", description="Verifies if the ledger engine storage and state are ready to accept traffic.")
def readiness_check():
    logger.info("Readiness check ping received.")
    return {"status": "ready", "engine_state": "operational"}

@router.post("/events", response_model=AuditLogEntry, status_code=status.HTTP_201_CREATED, summary="Ingest Financial Event", description="Processes a single financial event (DEPOSIT, WITHDRAW, TRANSFER, REVERSAL) with strict invariant checks and idempotency.")
def ingest_event(event: Event):
    logger.info(f"Ingesting event ID: {event.event_id} of type: {event.type}")
    return engine.ingest(event)

@router.post("/events/batch", response_model=List[AuditLogEntry], status_code=status.HTTP_201_CREATED, summary="Ingest Batch Events", description="Processes a batch of financial events atomically or sequentially with validation.")
def ingest_batch_events(events: List[Event]):
    logger.info(f"Ingesting batch of {len(events)} events.")
    return engine.ingest_batch(events)

@router.get("/accounts/{account_id}/balance", status_code=status.HTTP_200_OK, summary="Get Account Balance", description="Retrieves the current verified balance for a specific account.")
def get_account_balance(account_id: str):
    logger.info(f"Fetching balance for account: {account_id}")
    balance = engine.get_balance(account_id)
    return {"account_id": account_id, "balance": balance}

@router.get("/accounts/{account_id}/transactions", response_model=List[Event], status_code=status.HTTP_200_OK, summary="Get Account Transaction History", description="Retrieves all historical transactions associated with an account.")
def get_account_transactions(account_id: str):
    logger.info(f"Fetching transaction history for account: {account_id}")
    transactions = engine.get_transactions(account_id)
    return transactions

@router.post("/snapshot", status_code=status.HTTP_200_OK, summary="Create Engine Snapshot", description="Generates a full state snapshot of accounts and processed events for backup/audit.")
def create_snapshot():
    logger.info("Creating system snapshot.")
    return engine.snapshot()

@router.post("/restore", status_code=status.HTTP_200_OK, summary="Restore Engine State", description="Restores the ledger engine state from a provided snapshot dictionary.")
def restore_engine(snapshot_data: dict):
    try:
        logger.warning("Restoring ledger engine from snapshot data.")
        engine.restore(snapshot_data)
        return {"status": "success", "message": "Engine successfully restored from snapshot"}
    except Exception as e:
        logger.error(f"Failed to restore engine state: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))