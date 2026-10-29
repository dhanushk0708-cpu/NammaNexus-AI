from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.endpoints.spotfix import router as spotfix_router
from app.api.v1.endpoints.nammaserve import router as nammaserve_router
from app.api.v1.endpoints.nammaserve_research import (
    booking_router,
    router as nammaserve_research_router,
)


app = FastAPI(
    title="NammaNexus AI API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    spotfix_router,
    prefix="/api/v1",
)
app.include_router(
    nammaserve_router,
    prefix="/api/v1",
)
app.include_router(
    nammaserve_research_router,
    prefix="/api/v1",
)
app.include_router(
    booking_router,
    prefix="/api/v1",
)


@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }
