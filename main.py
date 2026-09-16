from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
import threading

app = FastAPI(
    title="Financial Ledger Engine",
    description="Adversarial-resilient transactional financial ledger engine with concurrency controls.",
    version="1.0.0"
)

# Pydantic Models for Request and Response Validation
class TransactionRequest(BaseModel):
    transaction_id: str
    account_id: str
    amount: float = Field(..., gt=0, description="Transaction amount must be greater than zero")
    transaction_type: str = Field(..., pattern="^(DEPOSIT|WITHDRAWAL|TRANSFER)$")
    target_account_id: Optional[str] = None

class LedgerResponse(BaseModel):
    status: str
    message: str
    balance: float
    transaction_id: str

# In-memory storage and thread-safety lock
ledger_db = {}
account_balances = {}
ledger_lock = threading.Lock()

@app.get("/")
def read_root():
    """Root endpoint to verify the service is running live."""
    return {"message": "Financial Ledger Engine is running successfully!"}

@app.post("/transaction", response_model=LedgerResponse)
def process_transaction(req: TransactionRequest):
    with ledger_lock:
        # Idempotency check
        if req.transaction_id in ledger_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Idempotency violation: Transaction ID already processed."
            )
        
        # Initialize accounts if not present
        if req.account_id not in account_balances:
            account_balances[req.account_id] = 0.0
            
        if req.target_account_id and req.target_account_id not in account_balances:
            account_balances[req.target_account_id] = 0.0

        # Process types
        if req.transaction_type == "DEPOSIT":
            account_balances[req.account_id] += req.amount
            current_balance = account_balances[req.account_id]

        elif req.transaction_type == "WITHDRAWAL":
            if account_balances[req.account_id] < req.amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Insufficient funds for withdrawal."
                )
            account_balances[req.account_id] -= req.amount
            current_balance = account_balances[req.account_id]

        elif req.transaction_type == "TRANSFER":
            if not req.target_account_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Target account ID is required for transfers."
                )
            if account_balances[req.account_id] < req.amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Insufficient funds for transfer."
                )
            account_balances[req.account_id] -= req.amount
            account_balances[req.target_account_id] += req.amount
            current_balance = account_balances[req.account_id]
        
        # Record transaction history
        ledger_db[req.transaction_id] = req.dict()

        return {
            "status": "SUCCESS",
            "message": f"Successfully processed {req.transaction_type}",
            "balance": current_balance,
            "transaction_id": req.transaction_id
        }

@app.get("/balance/{account_id}")
def get_balance(account_id: str):
    with ledger_lock:
        balance = account_balances.get(account_id, 0.0)
        return {"account_id": account_id, "balance": balance}