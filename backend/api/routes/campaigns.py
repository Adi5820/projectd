from typing import Any, Optional
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
import structlog

from backend.api.dependencies import (
    get_ad_repo,
    get_campaign_repo,
    get_db,
    get_job_manager,
)
from backend.db.repositories.ad_repo import AdRepository
from backend.db.repositories.campaign_repo import CampaignRepository
from backend.jobs.manager import JobManager
from backend.jobs.worker import run_full_generation_job
from backend.models.ad_copy import AdCopyResponse
from backend.models.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignStatus,
)
from backend.models.job import JobType
from backend.models.poster import PosterResponse
from backend.models.video import VideoResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new advertising campaign",
)
async def create_campaign(
    payload: CampaignCreate,
    repo: CampaignRepository = Depends(get_campaign_repo),
) -> CampaignResponse:
    campaign = await repo.create(payload)
    return CampaignResponse.model_validate(campaign)


@router.get(
    "",
    response_model=dict,
    summary="List all campaigns with pagination",
)
async def list_campaigns(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status_filter: Optional[CampaignStatus] = Query(default=None, alias="status"),
    repo: CampaignRepository = Depends(get_campaign_repo),
) -> dict:
    items, total = await repo.list_all(skip=skip, limit=limit, status=status_filter)
    return {
        "items": [CampaignResponse.model_validate(c) for c in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get(
    "/{campaign_id}",
    summary="Get campaign details by ID",
)
async def get_campaign(
    campaign_id: str,
    repo: CampaignRepository = Depends(get_campaign_repo),
    ad_repo: AdRepository = Depends(get_ad_repo),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Return campaign object or full campaign bundle with assets."""
    campaign = await repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    # Fetch associated assets
    ads = await ad_repo.get_by_campaign(campaign_id)
    ad_copies = [AdCopyResponse.model_validate(a) for a in ads]

    poster_cursor = db.posters.find({"campaign_id": campaign_id}).sort("created_at", -1)
    posters = []
    async for p in poster_cursor:
        p["_id"] = str(p["_id"])
        posters.append(PosterResponse.model_validate(p))

    video_cursor = db.videos.find({"campaign_id": campaign_id}).sort("created_at", -1)
    videos = []
    async for v in video_cursor:
        v["_id"] = str(v["_id"])
        videos.append(VideoResponse.model_validate(v))

    camp_resp = CampaignResponse.model_validate(campaign)

    # Return unified response that satisfies both CampaignResponse and CampaignDetailResponse
    result = camp_resp.model_dump()
    result["campaign"] = camp_resp.model_dump()
    result["ad_copies"] = [a.model_dump() for a in ad_copies]
    result["posters"] = [p.model_dump() for p in posters]
    result["videos"] = [v.model_dump() for v in videos]
    result["stats"] = {
        "ad_copies_count": sum(len(a.variations) for a in ad_copies),
        "posters_count": len(posters),
        "videos_count": len(videos),
    }
    return result


@router.post(
    "/{campaign_id}/generate",
    summary="Trigger end-to-end multi-agent campaign generation",
)
async def trigger_full_generation(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    repo: CampaignRepository = Depends(get_campaign_repo),
    job_manager: JobManager = Depends(get_job_manager),
) -> dict:
    """Trigger the multi-agent generation pipeline in the background."""
    campaign = await repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    job = await job_manager.create_job(
        campaign_id=campaign_id,
        job_type=JobType.FULL,
        total_steps=5,
    )

    background_tasks.add_task(run_full_generation_job, campaign_id, job.id)
    return {
        "job_id": job.id,
        "status": "queued",
        "message": "Full advertising generation started in background",
    }


@router.get(
    "/{campaign_id}/ad-copies",
    response_model=list[AdCopyResponse],
    summary="Get all ad copies for a campaign",
)
async def get_campaign_ad_copies(
    campaign_id: str,
    ad_repo: AdRepository = Depends(get_ad_repo),
) -> list[AdCopyResponse]:
    ads = await ad_repo.get_by_campaign(campaign_id)
    return [AdCopyResponse.model_validate(ad) for ad in ads]


@router.get(
    "/{campaign_id}/posters",
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
    "/{campaign_id}/videos",
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


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a campaign",
)
async def delete_campaign(
    campaign_id: str,
    repo: CampaignRepository = Depends(get_campaign_repo),
) -> None:
    deleted = await repo.delete(campaign_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
