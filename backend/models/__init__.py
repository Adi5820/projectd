from backend.models.ad_copy import (
    AdCopyInDB,
    AdCopyRequest,
    AdCopyResponse,
    AdVariation,
)
from backend.models.campaign import (
    CampaignCreate,
    CampaignGoal,
    CampaignInDB,
    CampaignResponse,
    CampaignStatus,
    Platform,
    Tone,
)
from backend.models.feedback import (
    ContentType,
    FeedbackCreate,
    FeedbackInDB,
    FeedbackResponse,
)
from backend.models.job import (
    JobInDB,
    JobProgress,
    JobResponse,
    JobResult,
    JobStatus,
    JobType,
)
from backend.models.poster import (
    AspectRatio,
    PosterInDB,
    PosterRequest,
    PosterResponse,
)
from backend.models.rag import (
    DocumentResponse,
    DocumentUpload,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from backend.models.video import (
    VideoInDB,
    VideoRequest,
    VideoResponse,
    VideoScene,
    VideoScript,
)

__all__ = [
    # Campaign
    "CampaignGoal",
    "Platform",
    "Tone",
    "CampaignStatus",
    "CampaignCreate",
    "CampaignInDB",
    "CampaignResponse",
    # Ad Copy
    "AdVariation",
    "AdCopyRequest",
    "AdCopyResponse",
    "AdCopyInDB",
    # Poster
    "AspectRatio",
    "PosterRequest",
    "PosterResponse",
    "PosterInDB",
    # Video
    "VideoScene",
    "VideoScript",
    "VideoRequest",
    "VideoResponse",
    "VideoInDB",
    # Job
    "JobStatus",
    "JobType",
    "JobProgress",
    "JobResult",
    "JobResponse",
    "JobInDB",
    # Feedback
    "ContentType",
    "FeedbackCreate",
    "FeedbackResponse",
    "FeedbackInDB",
    # RAG
    "DocumentUpload",
    "DocumentResponse",
    "SearchRequest",
    "SearchResult",
    "SearchResponse",
]
