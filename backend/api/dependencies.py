"""API Dependencies and Core Service Providers for Agentic Ads."""

from __future__ import annotations

import time
from typing import Any, Optional

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
import structlog

from backend.config import settings
from backend.db.mongodb import get_database
from backend.db.repositories.ad_repo import AdRepository
from backend.db.repositories.campaign_repo import CampaignRepository
from backend.db.repositories.feedback_repo import FeedbackRepository
from backend.db.repositories.job_repo import JobRepository
from backend.jobs.manager import JobManager

logger = structlog.get_logger(__name__)

# Module-level singletons
_orchestrator_instance: Optional[Any] = None
_chroma_client: Optional[Any] = None
_app_start_time: float = time.time()


def get_app_start_time() -> float:
    """Return the application startup timestamp for uptime computation."""
    return _app_start_time


def validate_object_id(id: str) -> str:
    """Validate that an ID string is a valid 24-character hexadecimal MongoDB ObjectId.

    Raises:
        HTTPException: 400 Bad Request if the ID format is invalid.

    Returns:
        The validated ID string.
    """
    if not id or not isinstance(id, str) or not ObjectId.is_valid(id):
        logger.warning("invalid_object_id_format", provided_id=id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ObjectId format: '{id}'. Must be a 24-character hexadecimal string.",
        )
    return id


def get_db() -> AsyncIOMotorDatabase:
    """Dependency that yields the active Motor MongoDB database instance."""
    return get_database()


def get_campaign_repo(db: AsyncIOMotorDatabase = Depends(get_db)) -> CampaignRepository:
    """Dependency for CampaignRepository."""
    return CampaignRepository(db)


def get_job_repo(db: AsyncIOMotorDatabase = Depends(get_db)) -> JobRepository:
    """Dependency for JobRepository."""
    return JobRepository(db)


def get_ad_repo(db: AsyncIOMotorDatabase = Depends(get_db)) -> AdRepository:
    """Dependency for AdRepository."""
    return AdRepository(db)


def get_feedback_repo(db: AsyncIOMotorDatabase = Depends(get_db)) -> FeedbackRepository:
    """Dependency for FeedbackRepository."""
    return FeedbackRepository(db)


def get_job_manager(job_repo: JobRepository = Depends(get_job_repo)) -> JobManager:
    """Dependency for JobManager."""
    return JobManager(job_repo)


def get_chroma_client() -> Any:
    """Get or create singleton ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        try:
            import chromadb
            persist_dir = getattr(settings, "CHROMA_PERSIST_DIR", "./chroma_db")
            _chroma_client = chromadb.PersistentClient(path=persist_dir)
            logger.info("chromadb_persistent_client_initialized", path=persist_dir)
        except Exception as exc:
            logger.error("chromadb_client_init_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize ChromaDB client: {exc}",
            )
    return _chroma_client


def get_orchestrator() -> Any:
    """Dependency that returns the Orchestrator singleton instance initialized with all providers."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        try:
            from backend.agents.orchestrator import AgentOrchestrator
            logger.info("instantiating_agent_orchestrator_singleton")
            _orchestrator_instance = AgentOrchestrator()
        except Exception as exc:
            logger.error("failed_to_initialize_agent_orchestrator", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize Agent Orchestrator: {exc}",
            )
    return _orchestrator_instance
