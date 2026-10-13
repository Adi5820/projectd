from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CampaignGoal(str, Enum):
    AWARENESS = "awareness"
    BRAND_AWARENESS = "brand_awareness"
    ENGAGEMENT = "engagement"
    CONVERSION = "conversion"
    SALES_CONVERSION = "sales_conversion"
    BRANDING = "branding"
    LEAD_GENERATION = "lead_generation"
    WEBSITE_TRAFFIC = "website_traffic"


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"
    GOOGLE_ADS = "google_ads"


class Tone(str, Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    LUXURY = "luxury"
    PLAYFUL = "playful"
    BOLD = "bold"
    INSPIRATIONAL = "inspirational"
    HUMOROUS = "humorous"
    URGENT = "urgent"


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class CampaignBase(BaseModel):
    brand_name: str = Field(..., min_length=1, max_length=100, description="Brand or company name")
    product_name: str = Field(..., min_length=1, max_length=150, description="Product or service name")
    product_description: str = Field(..., min_length=1, max_length=2500, description="Detailed product description")
    industry: str = Field(..., min_length=1, max_length=100, description="Industry or business domain")
    target_audience: str = Field(..., min_length=1, max_length=500, description="Target demographic and audience persona")
    campaign_goal: CampaignGoal = Field(..., description="Primary objective of the campaign")
    platforms: list[Platform] = Field(..., min_length=1, description="Target marketing platforms")
    tone: Tone = Field(..., description="Brand voice and messaging tone")
    language: str = Field(default="English", max_length=50, description="Content language")
    additional_context: Optional[str] = Field(default=None, max_length=2000, description="Extra context, constraints, or guidelines")


class CampaignCreate(CampaignBase):
    """Payload for creating a new ad campaign."""
    pass


class CampaignInDB(CampaignBase):
    """Database representation of a campaign."""
    id: str = Field(..., alias="_id", description="Unique campaign ID (MongoDB _id)")
    status: CampaignStatus = Field(default=CampaignStatus.DRAFT, description="Current campaign status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class CampaignResponse(CampaignBase):
    """API response model for a campaign."""
    id: str = Field(..., description="Unique campaign ID")
    status: CampaignStatus = Field(..., description="Current campaign status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
