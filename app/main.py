from fastapi import FastAPI
from app.api import pwa, ussd

app = FastAPI(
    title="MamaAfya API Gateway",
    description="Production API handling PWA ingestion and USSD webhooks.",
    version="1.0.0"
)

# Include the routers we just built
app.include_router(pwa.router, prefix="/api/pwa", tags=["PWA Endpoints"])
app.include_router(ussd.router, prefix="/api/ussd", tags=["USSD Webhooks"])

@app.get("/")
def health_check():
    return {"status": "MamaAfya Backend is healthy and running."}