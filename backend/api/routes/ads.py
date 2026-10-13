from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
import structlog

from backend.api.dependencies import get_ad_repo, get_campaign_repo, get_job_manager
from backend.db.repositories.ad_repo import AdRepository
from backend.db.repositories.campaign_repo import CampaignRepository
from backend.jobs.manager import JobManager
from backend.jobs.worker import run_ad_copy_generation_job
from backend.models.ad_copy import AdCopyRequest, AdCopyResponse
from backend.models.job import JobType

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/ads", tags=["ads"])


@router.post(
    "/generate",
    summary="Trigger targeted ad copy generation",
)
async def generate_ad_copy(
    payload: AdCopyRequest,
    background_tasks: BackgroundTasks,
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    job_manager: JobManager = Depends(get_job_manager),
) -> dict:
    """Generate ad copy variations for a campaign in the background."""
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
        "message": "Ad copy generation job started",
    }


@router.get(
    "/campaign/{campaign_id}",
    response_model=list[AdCopyResponse],
    summary="Get all ad copies for a campaign",
)
async def get_campaign_ads(
    campaign_id: str,
    ad_repo: AdRepository = Depends(get_ad_repo),
) -> list[AdCopyResponse]:
    ads = await ad_repo.get_by_campaign(campaign_id)
    return [AdCopyResponse.model_validate(ad) for ad in ads]


@router.get(
    "/{ad_id}",
    response_model=AdCopyResponse,
    summary="Get ad copy by ID",
)
async def get_ad_by_id(
    ad_id: str,
    ad_repo: AdRepository = Depends(get_ad_repo),
) -> AdCopyResponse:
    ad = await ad_repo.get_by_id(ad_id)
    if not ad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad copy not found")
    return AdCopyResponse.model_validate(ad)


@router.delete(
    "/{ad_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an ad copy",
)
async def delete_ad(
    ad_id: str,
    ad_repo: AdRepository = Depends(get_ad_repo),
) -> None:
    deleted = await ad_repo.delete(ad_id) if hasattr(ad_repo, "delete") else False
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad copy not found")
