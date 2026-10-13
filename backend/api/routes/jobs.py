from fastapi import APIRouter, Depends, HTTPException, Query, status
import structlog

from backend.api.dependencies import get_job_manager
from backend.jobs.manager import JobManager
from backend.models.job import JobResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get background generation job status",
)
async def get_job_status(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager),
) -> JobResponse:
    job = await job_manager.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get(
    "/campaign/{campaign_id}",
    response_model=list[JobResponse],
    summary="List all background jobs for a campaign",
)
async def list_campaign_jobs(
    campaign_id: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    job_manager: JobManager = Depends(get_job_manager),
) -> list[JobResponse]:
    return await job_manager.list_campaign_jobs(campaign_id=campaign_id, skip=skip, limit=limit)
