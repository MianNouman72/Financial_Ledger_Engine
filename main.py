from fastapi import FastAPI
from api import router

app = FastAPI(
    title="Financial Ledger Engine",
    version="2.0.0",
    description="An enterprise-grade, ACID-compliant financial ledger engine handling high-integrity transactions."
)

# Include the API router
app.include_router(router)

@app.get("/")
def root():
    return {"message": "Financial Ledger Engine is running. Visit /docs for documentation."}