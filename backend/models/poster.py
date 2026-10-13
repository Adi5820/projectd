from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AspectRatio(str, Enum):
    SQUARE = "1:1"
    PORTRAIT_4_5 = "4:5"
    VERTICAL_9_16 = "9:16"
    LANDSCAPE_16_9 = "16:9"


class PosterRequest(BaseModel):
    """Request payload for generating an advertising poster."""
    campaign_id: str = Field(..., description="ID of the associated campaign")
    platform: str = Field(..., description="Target platform (e.g., instagram, facebook)")
    aspect_ratio: AspectRatio = Field(default=AspectRatio.SQUARE, description="Visual aspect ratio")
    style_preferences: Optional[str] = Field(default=None, description="Aesthetic style preferences (e.g. minimalist, 3D render, cyberpunk)")
    include_text_overlay: bool = Field(default=True, description="Whether to include text overlay or badge")


class PosterResponse(BaseModel):
    """API response model for generated poster."""
    id: str = Field(..., description="Unique poster document ID")
    campaign_id: str = Field(..., description="ID of the associated campaign")
    image_url: str = Field(..., description="URL or relative path to high-resolution poster")
    thumbnail_url: Optional[str] = Field(default=None, description="URL or relative path to thumbnail")
    prompt: Optional[str] = Field(default="", description="Prompt used")
    prompt_used: Optional[str] = Field(default="", description="Final text prompt used for image generation")
    provider: str = Field(default="FLUX.1", description="Image generation provider (e.g. Together AI, Stability AI)")
    model_used: str = Field(default="FLUX.1-schnell", description="Model identifier used")
    aspect_ratio: str = Field(default="1:1", description="Aspect ratio of generated poster")
    platform: Optional[str] = Field(default=None, description="Target platform")
    status: str = Field(default="completed", description="Status of poster generation")
    generation_time_ms: float = Field(default=0.0, description="Time taken to generate poster in milliseconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class PosterInDB(BaseModel):
    """Database representation of a generated poster."""
    id: str = Field(..., alias="_id", description="Unique poster ID (MongoDB _id)")
    campaign_id: str = Field(..., description="ID of the associated campaign")
    platform: str = Field(..., description="Target platform")
    image_url: str = Field(..., description="Path or URL to poster file")
    thumbnail_url: str = Field(..., description="Path or URL to thumbnail file")
    prompt_used: str = Field(..., description="Text prompt used")
    provider: str = Field(..., description="Image provider")
    model_used: str = Field(..., description="Model name")
    aspect_ratio: str = Field(..., description="Aspect ratio")
    status: str = Field(default="completed", description="Generation status")
    generation_time_ms: float = Field(..., description="Generation latency in milliseconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
