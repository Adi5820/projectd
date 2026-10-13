from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AdVariation(BaseModel):
    """A single marketing ad variation."""
    headline: str = Field(..., description="Catchy headline for the ad")
    description: str = Field(..., description="Body copy or main promotional description")
    caption: str = Field(..., description="Social media caption suitable for posting")
    hashtags: list[str] = Field(default_factory=list, description="Relevant marketing hashtags")
    call_to_action: str = Field(..., description="Actionable call to action (CTA)")
    slogan: str = Field(..., description="Memorable slogan or punchline")


class AdCopyRequest(BaseModel):
    """Request payload for generating ad copy variations."""
    campaign_id: str = Field(..., description="ID of the associated campaign")
    platform: Optional[str] = Field(default=None, description="Optional target platform (e.g. instagram, facebook)")
    num_variations: int = Field(default=3, ge=1, le=10, description="Number of variations to generate (1 to 10)")


class AdCopyResponse(BaseModel):
    """API response model for generated ad copy."""
    id: str = Field(..., description="Unique ad copy document ID")
    campaign_id: str = Field(..., description="ID of the associated campaign")
    platform: Optional[str] = Field(default=None, description="Target platform")
    variations: list[AdVariation] = Field(..., description="List of generated ad variations")
    model_used: str = Field(default="gemini-2.0-flash", description="LLM model identifier used for generation")
    generation_time_ms: float = Field(default=0.0, description="Time taken to generate copy in milliseconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class AdCopyInDB(BaseModel):
    """Database representation of ad copy variations."""
    id: str = Field(..., alias="_id", description="Unique ad copy ID (MongoDB _id)")
    campaign_id: str = Field(..., description="ID of the associated campaign")
    platform: Optional[str] = Field(default=None, description="Target platform")
    variations: list[AdVariation] = Field(..., description="List of generated ad variations")
    model_used: str = Field(..., description="LLM model identifier used for generation")
    generation_time_ms: float = Field(..., description="Generation latency in milliseconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
