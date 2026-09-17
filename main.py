from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Financial Ledger Engine",
    description="An enterprise-grade, ACID-compliant financial ledger engine handling high-integrity transactions.",
    version="2.0.0"
)

# Custom Exception for Business Logic Errors
class LedgerException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

# Global Handler for Ledger Business Errors (Prevents raw trace leaks)
@app.exception_handler(LedgerException)
async def ledger_exception_handler(request: Request, exc: LedgerException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "ERROR",
            "error_code": "LEDGER_BUSINESS_ERROR",
            "message": exc.message
        }
    )

# Global Unexpected Error Handler (Production safety net)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status": "ERROR",
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected internal error occurred. Please try again later."
        }
    )

# Include your existing router (jo api.py ya routes se aa raha hai)
try:
    from api import router as api_router
    app.include_router(api_router)
except ImportError:
    pass