from typing import Optional
from fastapi import APIRouter, Depends, Query, status
import structlog

from backend.api.dependencies import get_feedback_repo
from backend.db.repositories.feedback_repo import FeedbackRepository
from backend.models.feedback import (
    FeedbackCreate,
    FeedbackResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit user feedback on generated content",
)
async def submit_feedback(
    payload: FeedbackCreate,
    repo: FeedbackRepository = Depends(get_feedback_repo),
) -> FeedbackResponse:
    feedback = await repo.create(payload)
    return FeedbackResponse.model_validate(feedback)


@router.get(
    "/campaign/{campaign_id}",
    response_model=dict,
    summary="Get all feedback and average rating for a campaign",
)
async def get_campaign_feedback(
    campaign_id: str,
    content_type: Optional[str] = Query(default=None),
    repo: FeedbackRepository = Depends(get_feedback_repo),
) -> dict:
    feedbacks = await repo.get_by_campaign(campaign_id)
    avg_rating = await repo.get_average_rating(campaign_id, content_type=content_type)
    return {
        "campaign_id": campaign_id,
        "average_rating": avg_rating,
        "feedbacks": [FeedbackResponse.model_validate(f) for f in feedbacks],
    }


@router.get(
    "/content/{content_id}",
    response_model=list[FeedbackResponse],
    summary="Get feedback for a specific generated asset",
)
async def get_content_feedback(
    content_id: str,
    repo: FeedbackRepository = Depends(get_feedback_repo),
) -> list[FeedbackResponse]:
    feedbacks = await repo.get_by_content(content_id)
    return [FeedbackResponse.model_validate(f) for f in feedbacks]
