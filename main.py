import json
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ledger import LedgerEngine

app = FastAPI(title="Adversarial Financial Ledger Engine", version="2.0.0")
ledger = LedgerEngine()

class EventModel(BaseModel):
    event_id: str
    account_id: str
    type: str
    amount: float
    timestamp: str
    target_account_id: str | None = None
    original_event_id: str | None = None

@app.post("/events/ingest")
def ingest_event(event: EventModel):
    result = ledger.ingest(event.model_dump())
    return result

@app.post("/events/stream")
async def stream_events(request: Request):
    """
    Optimized NDJSON streaming endpoint designed to handle massive payloads 
    line-by-line without exhausting server memory.
    """
    async def event_generator():
        async for line in request.stream():
            if not line.strip():
                continue
            try:
                line_str = line.decode("utf-8").strip()
                if line_str:
                    event_data = json.loads(line_str)
                    result = ledger.ingest(event_data)
                    yield json.dumps(result) + "\n"
            except Exception as e:
                error_response = {"status": "ERROR", "message": str(e)}
                yield json.dumps(error_response) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@app.get("/accounts/{account_id}/balance")
def get_balance(account_id: str):
    balance = ledger.get_balance(account_id)
    return {"account_id": account_id, "balance": balance}