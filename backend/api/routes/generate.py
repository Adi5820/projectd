"""API routes for triggering AI generation jobs."""

from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
import structlog

from backend.api.dependencies import get_campaign_repo, get_job_manager
from backend.db.repositories.campaign_repo import CampaignRepository
from backend.jobs.manager import JobManager
from backend.jobs.worker import (
    run_ad_copy_generation_job,
    run_full_generation_job,
    run_poster_generation_job,
    run_video_generation_job,
)
from backend.models.ad_copy import AdCopyRequest
from backend.models.job import JobType

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/generate", tags=["generate"])


class GenerateFullRequest(BaseModel):
    campaign_id: str = Field(..., description="Campaign ID to generate full suite for")


class GeneratePosterRequest(BaseModel):
    campaign_id: str = Field(..., description="Campaign ID")
    aspect_ratio: Optional[str] = Field(default="1:1", description="Aspect ratio")
    platform: Optional[str] = Field(default="instagram", description="Target platform")
    prompt_override: Optional[str] = Field(default=None, description="Prompt override")


class GenerateVideoRequest(BaseModel):
    campaign_id: str = Field(..., description="Campaign ID")
    duration_seconds: Optional[int] = Field(default=15, description="Duration in seconds")
    platform: Optional[str] = Field(default="instagram", description="Target platform")
    script_prompt: Optional[str] = Field(default=None, description="Prompt override")


@router.post(
    "/full",
    summary="Trigger full multi-agent generation pipeline",
)
async def generate_full(
    payload: GenerateFullRequest,
    background_tasks: BackgroundTasks,
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    job_manager: JobManager = Depends(get_job_manager),
) -> dict:
    campaign = await campaign_repo.get_by_id(payload.campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    job = await job_manager.create_job(
        campaign_id=payload.campaign_id,
        job_type=JobType.FULL,
        total_steps=5,
    )

    background_tasks.add_task(run_full_generation_job, payload.campaign_id, job.id)
    return {
        "job_id": job.id,
        "status": "queued",
        "message": "Full generation started",
    }


@router.post(
    "/ad-copy",
    summary="Trigger ad copy generation",
)
async def generate_ad_copy(
    payload: AdCopyRequest,
    background_tasks: BackgroundTasks,
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    job_manager: JobManager = Depends(get_job_manager),
) -> dict:
    campaign = await campaign_repo.get_by_id(payload.campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    job = await job_manager.create_job(
        campaign_id=payload.campaign_id,
        job_type=JobType.COPY,
        total_steps=3,
    )

    background_tasks.add_task(
        run_ad_copy_generation_job,
        campaign_id=payload.campaign_id,
        job_id=job.id,
        platform=payload.platform or (campaign.platforms[0] if campaign.platforms else "instagram"),
        num_variations=payload.num_variations or 3,
    )

    return {
        "job_id": job.id,
        "status": "queued",
        "message": "Ad copy generation started",
    }


@router.post(
    "/poster",
    summary="Trigger poster generation",
)
async def generate_poster(
    payload: GeneratePosterRequest,
    background_tasks: BackgroundTasks,
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    job_manager: JobManager = Depends(get_job_manager),
) -> dict:
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
        "message": "Poster generation started",
    }


@router.post(
    "/video",
    summary="Trigger video production",
)
async def generate_video(
    payload: GenerateVideoRequest,
    background_tasks: BackgroundTasks,
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    job_manager: JobManager = Depends(get_job_manager),
) -> dict:
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
        "message": "Video production started",
    }
