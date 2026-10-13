from datetime import datetime
from typing import Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
import structlog

from backend.models.job import (
    JobInDB,
    JobProgress,
    JobResult,
    JobStatus,
    JobType,
)

logger = structlog.get_logger(__name__)


def _query_by_id(id_val: str) -> dict:
    if ObjectId.is_valid(id_val):
        return {"$or": [{"_id": ObjectId(id_val)}, {"_id": id_val}]}
    return {"_id": id_val}


class JobRepository:
    """MongoDB repository for tracking asynchronous generation jobs."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db.jobs

    async def create(
        self, campaign_id: str, job_type: JobType, total_steps: int = 1
    ) -> JobInDB:
        """Create a new job tracking record."""
        now = datetime.utcnow()
        doc = {
            "_id": str(ObjectId()),
            "campaign_id": campaign_id,
            "job_type": job_type.value,
            "status": JobStatus.QUEUED.value,
            "progress": {
                "current_step": "Queued",
                "steps_completed": 0,
                "total_steps": max(1, total_steps),
                "message": "Job queued for execution",
            },
            "result": None,
            "error": None,
            "started_at": None,
            "completed_at": None,
            "created_at": now,
            "updated_at": now,
        }
        await self.collection.insert_one(doc)
        logger.info("Job record created in MongoDB", job_id=doc["_id"], job_type=job_type.value)
        return JobInDB(**doc)

    async def get_by_id(self, job_id: str) -> Optional[JobInDB]:
        """Fetch a job record by ID."""
        doc = await self.collection.find_one(_query_by_id(job_id))
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return JobInDB(**doc)

    async def update_status(self, job_id: str, status: JobStatus) -> Optional[JobInDB]:
        """Update job status and set appropriate lifecycle timestamps."""
        now = datetime.utcnow()
        update_fields: dict = {
            "status": status.value,
            "updated_at": now,
        }

        if status == JobStatus.RUNNING:
            update_fields["started_at"] = now
        elif status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.PARTIAL):
            update_fields["completed_at"] = now

        updated_doc = await self.collection.find_one_and_update(
            _query_by_id(job_id),
            {"$set": update_fields},
            return_document=True,
        )
        if not updated_doc:
            return None
        updated_doc["_id"] = str(updated_doc["_id"])
        logger.info("Updated job status", job_id=job_id, status=status.value)
        return JobInDB(**updated_doc)

    async def update_progress(
        self,
        job_id: str,
        current_step: str,
        steps_completed: int,
        total_steps: int,
        message: str,
    ) -> Optional[JobInDB]:
        """Update job progress fields."""
        now = datetime.utcnow()
        progress_payload = {
            "current_step": current_step,
            "steps_completed": steps_completed,
            "total_steps": total_steps,
            "message": message,
        }
        updated_doc = await self.collection.find_one_and_update(
            _query_by_id(job_id),
            {
                "$set": {
                    "progress": progress_payload,
                    "updated_at": now,
                }
            },
            return_document=True,
        )
        if not updated_doc:
            return None
        updated_doc["_id"] = str(updated_doc["_id"])
        return JobInDB(**updated_doc)

    async def set_result(self, job_id: str, result: JobResult) -> Optional[JobInDB]:
        """Mark job as completed and attach the generated assets result."""
        now = datetime.utcnow()
        updated_doc = await self.collection.find_one_and_update(
            _query_by_id(job_id),
            {
                "$set": {
                    "status": JobStatus.COMPLETED.value,
                    "result": result.model_dump(),
                    "completed_at": now,
                    "updated_at": now,
                    "progress.current_step": "Completed",
                    "progress.steps_completed": 1,
                    "progress.total_steps": 1,
                    "progress.message": "All steps completed successfully",
                }
            },
            return_document=True,
        )
        if not updated_doc:
            return None
        updated_doc["_id"] = str(updated_doc["_id"])
        logger.info("Job marked completed with results", job_id=job_id)
        return JobInDB(**updated_doc)

    async def set_error(self, job_id: str, error_message: str) -> Optional[JobInDB]:
        """Mark job as failed with an error message."""
        now = datetime.utcnow()
        updated_doc = await self.collection.find_one_and_update(
            _query_by_id(job_id),
            {
                "$set": {
                    "status": JobStatus.FAILED.value,
                    "error": error_message,
                    "completed_at": now,
                    "updated_at": now,
                    "progress.message": f"Job failed: {error_message}",
                }
            },
            return_document=True,
        )
        if not updated_doc:
            return None
        updated_doc["_id"] = str(updated_doc["_id"])
        logger.error("Job marked failed", job_id=job_id, error=error_message)
        return JobInDB(**updated_doc)

    async def list_by_campaign(
        self, campaign_id: str, skip: int = 0, limit: int = 20
    ) -> list[JobInDB]:
        """List all background jobs associated with a specific campaign."""
        cursor = (
            self.collection.find({"campaign_id": campaign_id})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        jobs: list[JobInDB] = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            jobs.append(JobInDB(**doc))
        return jobs
