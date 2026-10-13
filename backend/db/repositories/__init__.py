from backend.db.repositories.ad_repo import AdRepository
from backend.db.repositories.campaign_repo import CampaignRepository
from backend.db.repositories.feedback_repo import FeedbackRepository
from backend.db.repositories.job_repo import JobRepository

__all__ = [
    "CampaignRepository",
    "JobRepository",
    "AdRepository",
    "FeedbackRepository",
]
