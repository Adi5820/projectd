from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class JobType(str, Enum):
    FULL = "full"
    COPY = "copy"
    POSTER = "poster"
    VIDEO = "video"


class JobProgress(BaseModel):
    """Real-time progress representation of an asynchronous job."""
    current_step: str = Field(default="Initializing", description="Current execution phase description")
    steps_completed: int = Field(default=0, ge=0, description="Number of subtasks finished")
    total_steps: int = Field(default=1, ge=1, description="Total number of steps planned")
    message: str = Field(default="Job queued", description="User-friendly status message")

    @property
    def percentage(self) -> float:
        if self.total_steps == 0:
            return 0.0
        return round((self.steps_completed / self.total_steps) * 100.0, 1)


class JobResult(BaseModel):
    """Identifiers of generated assets associated with this job."""
    ad_copy_id: Optional[str] = Field(default=None, description="Generated ad copy document ID")
    poster_id: Optional[str] = Field(default=None, description="Generated poster document ID")
    video_id: Optional[str] = Field(default=None, description="Generated video document ID")


class JobResponse(BaseModel):
    """API response model for an async generation job."""
    id: str = Field(..., description="Unique job ID")
    campaign_id: str = Field(..., description="ID of associated campaign")
    job_type: JobType = Field(..., description="Job execution category")
    status: JobStatus = Field(default=JobStatus.QUEUED, description="Lifecycle status")
    progress: JobProgress = Field(default_factory=JobProgress, description="Current progress status")
    result: Optional[JobResult] = Field(default=None, description="Outputs upon successful completion")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    started_at: Optional[datetime] = Field(default=None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    @computed_field
    @property
    def job_id(self) -> str:
        return self.id

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class JobInDB(BaseModel):
    """Database model for background job tracking."""
    id: str = Field(..., alias="_id", description="Unique job ID (MongoDB _id)")
    campaign_id: str = Field(..., description="ID of associated campaign")
    job_type: JobType = Field(..., description="Job type")
    status: JobStatus = Field(default=JobStatus.QUEUED, description="Lifecycle status")
    progress: JobProgress = Field(default_factory=JobProgress, description="Progress details")
    result: Optional[JobResult] = Field(default=None, description="Job results")
    error: Optional[str] = Field(default=None, description="Error details if any")
    started_at: Optional[datetime] = Field(default=None, description="Execution started timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Execution finished timestamp")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
