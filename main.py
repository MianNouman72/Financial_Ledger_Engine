import json
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ledger import LedgerEngine

app = FastAPI(title="Financial Ledger Engine", version="1.0.0")
ledger = LedgerEngine()

class EventModel(BaseModel):
    event_id: str
    account_id: str
    type: str
    amount: float
    timestamp: str
    target_account_id: str | None = None

@app.post("/events/ingest")
def ingest_event(event: EventModel):
    """Ingests a single financial event."""
    result = ledger.ingest(event.model_dump())
    return result

@app.post("/events/stream")
async def stream_events(request: Request):
    """
    Accepts an NDJSON (Newline-Delimited JSON) stream of events,
    processes them sequentially, and returns the results stream.
    """
    async def event_generator():
        async for line in request.stream():
            if not line.strip():
                continue
            try:
                event_data = json.loads(line.decode("utf-8"))
                result = ledger.ingest(event_data)
                yield json.dumps(result) + "\n"
            except Exception as e:
                error_response = {"status": "ERROR", "message": str(e)}
                yield json.dumps(error_response) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@app.get("/accounts/{account_id}/balance")
def get_balance(account_id: str):
    """Retrieves the current balance of an account."""
    balance = ledger.get_balance(account_id)
    return {"account_id": account_id, "balance": balance}

@app.get("/audit/logs")
def get_audit_logs():
    """Retrieves the system audit trail."""
    return {"audit_log": ledger.audit_log}

@app.get("/fraud/alerts")
def get_fraud_alerts():
    """Retrieves all logged fraud alerts."""
    return {"fraud_alerts": ledger.fraud_alerts}