from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.endpoints.spotfix import router as spotfix_router


app = FastAPI(
    title="NammaNexus AI API",
    version="1.0.0",
)


app.include_router(
    spotfix_router,
    prefix="/api/v1",
)


@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }