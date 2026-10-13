from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class VideoScene(BaseModel):
    """A single storyboard scene in the video."""
    scene_number: int = Field(..., description="Scene index sequence (1-indexed)")
    description: str = Field(..., description="Visual description of what appears in this scene")
    duration: float = Field(..., description="Scene duration in seconds")
    narration_text: str = Field(..., description="Narration or voiceover script for this scene")
    image_prompt: str = Field(..., description="AI image generation prompt for this scene frame")


class VideoScript(BaseModel):
    """Full script and storyboard for the video ad."""
    title: str = Field(..., description="Video concept title")
    scenes: list[VideoScene] = Field(..., min_length=1, description="List of sequential scenes")
    total_duration: float = Field(..., description="Sum of scene durations in seconds")


class VideoRequest(BaseModel):
    """Request payload for generating a promotional video ad."""
    campaign_id: str = Field(..., description="ID of the associated campaign")
    platform: str = Field(default="instagram", description="Target platform (e.g., instagram, youtube, tiktok)")
    duration_seconds: int = Field(default=15, ge=5, le=60, description="Target duration in seconds (max 60)")
    aspect_ratio: str = Field(default="9:16", description="Video aspect ratio (default 9:16 vertical)")
    include_narration: bool = Field(default=True, description="Whether to generate TTS voiceover narration")
    include_music: bool = Field(default=True, description="Whether to include background music track")


class VideoResponse(BaseModel):
    """API response model for generated video ad."""
    id: str = Field(..., description="Unique video document ID")
    campaign_id: str = Field(..., description="ID of the associated campaign")
    video_url: str = Field(..., description="Path or URL to generated MP4 video file")
    thumbnail_url: Optional[str] = Field(default=None, description="Path or URL to generated video thumbnail poster")
    script: Optional[Any] = Field(default=None, description="Generated video storyboard and script")
    status: str = Field(default="completed", description="Video generation status")
    duration_seconds: float = Field(default=15.0, description="Actual length of generated video in seconds")
    duration: Optional[float] = Field(default=None, description="Duration alias for frontend")
    generation_time_ms: float = Field(default=0.0, description="Time taken to render video in milliseconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class VideoInDB(BaseModel):
    """Database representation of generated video ad."""
    id: str = Field(..., alias="_id", description="Unique video ID (MongoDB _id)")
    campaign_id: str = Field(..., description="ID of the associated campaign")
    platform: str = Field(..., description="Target platform")
    video_url: str = Field(..., description="Path or URL to video file")
    thumbnail_url: str = Field(..., description="Path or URL to thumbnail file")
    script: VideoScript = Field(..., description="Video storyboard and script")
    status: str = Field(default="completed", description="Generation status")
    duration_seconds: float = Field(..., description="Video duration in seconds")
    generation_time_ms: float = Field(..., description="Rendering latency in milliseconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
