from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ContentType(str, Enum):
    COPY = "copy"
    POSTER = "poster"
    VIDEO = "video"


class FeedbackCreate(BaseModel):
    """Payload for submitting user feedback/rating on generated content."""
    campaign_id: str = Field(..., description="ID of associated campaign")
    content_type: ContentType = Field(..., description="Type of asset (copy, poster, video)")
    content_id: str = Field(..., description="ID of specific generated asset")
    rating: int = Field(..., ge=1, le=5, description="Quality rating from 1 to 5")
    comment: Optional[str] = Field(default=None, max_length=1000, description="Optional qualitative review or feedback")


class FeedbackResponse(BaseModel):
    """API response model for content feedback."""
    id: str = Field(..., description="Unique feedback ID")
    campaign_id: str = Field(..., description="ID of associated campaign")
    content_type: ContentType = Field(..., description="Asset type")
    content_id: str = Field(..., description="Asset ID")
    rating: int = Field(..., description="Rating (1-5)")
    comment: Optional[str] = Field(default=None, description="Feedback comment")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Submission timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class FeedbackInDB(BaseModel):
    """Database representation of content feedback."""
    id: str = Field(..., alias="_id", description="Unique feedback ID (MongoDB _id)")
    campaign_id: str = Field(..., description="ID of associated campaign")
    content_type: ContentType = Field(..., description="Asset type")
    content_id: str = Field(..., description="Asset ID")
    rating: int = Field(..., ge=1, le=5, description="Rating score")
    comment: Optional[str] = Field(default=None, description="User comment")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Submission timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
