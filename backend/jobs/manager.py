from datetime import datetime
from typing import Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
import structlog

from backend.db.repositories.job_repo import JobRepository
from backend.models.job import (
    JobInDB,
    JobProgress,
    JobResponse,
    JobResult,
    JobStatus,
    JobType,
)

logger = structlog.get_logger(__name__)


class JobManager:
    """Manages async job state both in-memory and persisted in MongoDB."""

    def __init__(self, job_repo: JobRepository) -> None:
        self.job_repo = job_repo
        # In-memory lookup for fast tracking of active tasks
        self._active_jobs: dict[str, dict[str, Any]] = {}

    async def create_job(
        self,
        campaign_id: str,
        job_type: JobType,
        total_steps: int = 1,
    ) -> JobResponse:
        """Create a new job record in MongoDB and register in-memory tracking."""
        job_in_db = await self.job_repo.create(
            campaign_id=campaign_id,
            job_type=job_type,
            total_steps=total_steps,
        )

        job_id = job_in_db.id
        self._active_jobs[job_id] = {
            "id": job_id,
            "campaign_id": campaign_id,
            "job_type": job_type,
            "status": JobStatus.QUEUED,
            "current_step": "Queued",
            "steps_completed": 0,
            "total_steps": total_steps,
            "message": "Job queued for execution",
            "result": None,
            "error": None,
            "created_at": job_in_db.created_at,
        }

        logger.info("JobManager created job", job_id=job_id, job_type=job_type.value)
        return self._to_response(job_in_db)

    async def start_job(self, job_id: str) -> None:
        """Mark job status as RUNNING in MongoDB and in-memory cache."""
        await self.job_repo.update_status(job_id, JobStatus.RUNNING)
        if job_id in self._active_jobs:
            self._active_jobs[job_id]["status"] = JobStatus.RUNNING
            self._active_jobs[job_id]["started_at"] = datetime.utcnow()
        logger.info("JobManager started job execution", job_id=job_id)

    async def update_progress(
        self,
        job_id: str,
        current_step: str,
        steps_completed: int,
        total_steps: int,
        message: str,
    ) -> None:
        """Update job progress steps and status message in both MongoDB and in-memory cache."""
        await self.job_repo.update_progress(
            job_id=job_id,
            current_step=current_step,
            steps_completed=steps_completed,
            total_steps=total_steps,
            message=message,
        )

        if job_id in self._active_jobs:
            self._active_jobs[job_id].update({
                "status": JobStatus.RUNNING,
                "current_step": current_step,
                "steps_completed": steps_completed,
                "total_steps": total_steps,
                "message": message,
            })
        logger.debug(
            "Job progress updated",
            job_id=job_id,
            step=current_step,
            progress=f"{steps_completed}/{total_steps}",
        )

    async def update_job(
        self,
        job_id: str,
        status: str,
        progress: int,
        message: str,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        """Compatibility method for orchestrator to update job status and percentage progress."""
        status_enum = JobStatus.RUNNING
        if status in ("completed", "partial_success", "success"):
            status_enum = JobStatus.COMPLETED
        elif status in ("failed", "error"):
            status_enum = JobStatus.FAILED

        await self.job_repo.update_progress(
            job_id=job_id,
            current_step=message,
            steps_completed=max(0, min(progress, 100)),
            total_steps=100,
            message=message,
        )
        if status_enum != JobStatus.RUNNING:
            await self.job_repo.update_status(job_id=job_id, status=status_enum)

        if job_id in self._active_jobs:
            self._active_jobs[job_id].update({
                "status": status_enum,
                "current_step": message,
                "steps_completed": max(0, min(progress, 100)),
                "total_steps": 100,
                "message": message,
            })


    async def complete_job(
        self,
        job_id: str,
        result: Optional[JobResult] = None,
    ) -> None:
        """Mark job as COMPLETED and attach generated assets."""
        res = result or JobResult()
        await self.job_repo.set_result(job_id=job_id, result=res)

        if job_id in self._active_jobs:
            self._active_jobs[job_id].update({
                "status": JobStatus.COMPLETED,
                "result": res.model_dump(),
                "completed_at": datetime.utcnow(),
                "current_step": "Completed",
                "message": "All generation steps completed successfully",
            })
            # Clean up after active completion
            self._active_jobs.pop(job_id, None)

        logger.info("JobManager completed job", job_id=job_id)

    async def fail_job(self, job_id: str, error_message: str) -> None:
        """Mark job as FAILED and log error message."""
        await self.job_repo.set_error(job_id=job_id, error_message=error_message)

        if job_id in self._active_jobs:
            self._active_jobs[job_id].update({
                "status": JobStatus.FAILED,
                "error": error_message,
                "completed_at": datetime.utcnow(),
                "message": f"Execution failed: {error_message}",
            })
            # Clean up after active failure
            self._active_jobs.pop(job_id, None)

        logger.error("JobManager recorded job failure", job_id=job_id, error=error_message)

    async def get_job_status(self, job_id: str) -> Optional[JobResponse]:
        """Fetch current job status from MongoDB, returning None if not found."""
        job_in_db = await self.job_repo.get_by_id(job_id)
        if not job_in_db:
            return None
        return self._to_response(job_in_db)

    async def list_campaign_jobs(
        self, campaign_id: str, skip: int = 0, limit: int = 20
    ) -> list[JobResponse]:
        """List all jobs associated with a campaign."""
        jobs_in_db = await self.job_repo.list_by_campaign(campaign_id, skip=skip, limit=limit)
        return [self._to_response(job) for job in jobs_in_db]

    def get_active_count(self) -> int:
        """Count of in-memory active jobs."""
        return len(self._active_jobs)

    @staticmethod
    def _to_response(job_in_db: JobInDB) -> JobResponse:
        """Convert JobInDB model to JobResponse."""
        return JobResponse(
            id=job_in_db.id,
            campaign_id=job_in_db.campaign_id,
            job_type=job_in_db.job_type,
            status=job_in_db.status,
            progress=job_in_db.progress,
            result=job_in_db.result,
            error=job_in_db.error,
            started_at=job_in_db.started_at,
            completed_at=job_in_db.completed_at,
            created_at=job_in_db.created_at,
        )
