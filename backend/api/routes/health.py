from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
import structlog

from backend.db.mongodb import mongodb_manager
from backend.api.dependencies import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", summary="System Health Check")
@router.get("/api/health", summary="System Health Check (API Prefix)")
async def health_check() -> dict:
    """Returns the operational status of the API and its database backends."""
    mongo_healthy = await mongodb_manager.health_check()
    return {
        "status": "healthy" if mongo_healthy else "degraded",
        "mongodb": mongo_healthy,
        "api_version": "1.0.0",
        "service": "Agentic Ads API",
    }
