from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
import structlog

from backend.api.dependencies import get_campaign_repo, get_db, get_job_manager
from backend.db.repositories.campaign_repo import CampaignRepository
from backend.jobs.manager import JobManager
from backend.jobs.worker import run_poster_generation_job
from backend.models.job import JobType
from backend.models.poster import PosterResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/posters", tags=["posters"])


class PosterGenerateRequest(BaseModel):
    campaign_id: str = Field(..., description="Campaign ID")
    aspect_ratio: Optional[str] = Field(default="1:1", description="Aspect ratio (1:1, 9:16, 16:9, 4:5)")
    platform: Optional[str] = Field(default="instagram", description="Target channel")
    prompt_override: Optional[str] = Field(default=None, description="Optional prompt override")


def _query_by_id(id_val: str) -> dict:
    if ObjectId.is_valid(id_val):
        return {"$or": [{"_id": ObjectId(id_val)}, {"_id": id_val}]}
    return {"_id": id_val}


@router.post(
    "/generate",
    summary="Trigger poster image generation",
)
async def generate_poster(
    payload: PosterGenerateRequest,
    background_tasks: BackgroundTasks,
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    job_manager: JobManager = Depends(get_job_manager),
) -> dict:
    """Generate a visual advertising poster in the background."""
    campaign = await campaign_repo.get_by_id(payload.campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    job = await job_manager.create_job(
        campaign_id=payload.campaign_id,
        job_type=JobType.POSTER,
        total_steps=3,
    )

    background_tasks.add_task(
        run_poster_generation_job,
        campaign_id=payload.campaign_id,
        job_id=job.id,
        aspect_ratio=payload.aspect_ratio or "1:1",
        platform=payload.platform or (campaign.platforms[0] if campaign.platforms else "instagram"),
    )

    return {
        "job_id": job.id,
        "status": "queued",
        "message": "Poster generation job started",
    }


@router.get(
    "/campaign/{campaign_id}",
    response_model=list[PosterResponse],
    summary="Get all generated posters for a campaign",
)
async def get_campaign_posters(
    campaign_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[PosterResponse]:
    cursor = db.posters.find({"campaign_id": campaign_id}).sort("created_at", -1)
    posters = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        posters.append(PosterResponse.model_validate(doc))
    return posters


@router.get(
    "/{poster_id}",
    response_model=PosterResponse,
    summary="Get poster by ID",
)
async def get_poster_by_id(
    poster_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> PosterResponse:
    doc = await db.posters.find_one(_query_by_id(poster_id))
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poster not found")
    doc["_id"] = str(doc["_id"])
    return PosterResponse.model_validate(doc)
