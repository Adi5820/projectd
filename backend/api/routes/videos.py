from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
import structlog

from backend.api.dependencies import get_campaign_repo, get_db, get_job_manager
from backend.db.repositories.campaign_repo import CampaignRepository
from backend.jobs.manager import JobManager
from backend.jobs.worker import run_video_generation_job
from backend.models.job import JobType
from backend.models.video import VideoResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/videos", tags=["videos"])


class VideoGenerateRequest(BaseModel):
    campaign_id: str = Field(..., description="Campaign ID")
    duration_seconds: Optional[int] = Field(default=15, ge=5, le=60, description="Duration in seconds")
    platform: Optional[str] = Field(default="instagram", description="Target platform")
    script_prompt: Optional[str] = Field(default=None, description="Optional prompt override")


def _query_by_id(id_val: str) -> dict:
    if ObjectId.is_valid(id_val):
        return {"$or": [{"_id": ObjectId(id_val)}, {"_id": id_val}]}
    return {"_id": id_val}


@router.post(
    "/generate",
    summary="Trigger promotional video generation",
)
async def generate_video(
    payload: VideoGenerateRequest,
    background_tasks: BackgroundTasks,
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    job_manager: JobManager = Depends(get_job_manager),
) -> dict:
    """Generate a multi-scene commercial video in the background."""
    campaign = await campaign_repo.get_by_id(payload.campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    job = await job_manager.create_job(
        campaign_id=payload.campaign_id,
        job_type=JobType.VIDEO,
        total_steps=5,
    )

    background_tasks.add_task(
        run_video_generation_job,
        campaign_id=payload.campaign_id,
        job_id=job.id,
        duration=payload.duration_seconds or 15,
        platform=payload.platform or (campaign.platforms[0] if campaign.platforms else "instagram"),
    )

    return {
        "job_id": job.id,
        "status": "queued",
        "message": "Video production job started",
    }


@router.get(
    "/campaign/{campaign_id}",
    response_model=list[VideoResponse],
    summary="Get all generated videos for a campaign",
)
async def get_campaign_videos(
    campaign_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[VideoResponse]:
    cursor = db.videos.find({"campaign_id": campaign_id}).sort("created_at", -1)
    videos = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        videos.append(VideoResponse.model_validate(doc))
    return videos


@router.get(
    "/{video_id}",
    response_model=VideoResponse,
    summary="Get video by ID",
)
async def get_video_by_id(
    video_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> VideoResponse:
    doc = await db.videos.find_one(_query_by_id(video_id))
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    doc["_id"] = str(doc["_id"])
    return VideoResponse.model_validate(doc)
