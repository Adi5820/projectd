from datetime import datetime
from typing import Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
import structlog

from backend.models.feedback import FeedbackCreate, FeedbackInDB

logger = structlog.get_logger(__name__)


def _query_by_id(id_val: str) -> dict:
    if ObjectId.is_valid(id_val):
        return {"$or": [{"_id": ObjectId(id_val)}, {"_id": id_val}]}
    return {"_id": id_val}


class FeedbackRepository:
    """MongoDB repository for managing user feedback and ratings."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db.feedback

    async def create(self, feedback: FeedbackCreate) -> FeedbackInDB:
        """Create a new feedback entry."""
        now = datetime.utcnow()
        doc = feedback.model_dump()
        doc.update({
            "_id": str(ObjectId()),
            "content_type": feedback.content_type.value if hasattr(feedback.content_type, "value") else str(feedback.content_type),
            "created_at": now,
            "updated_at": now,
        })
        await self.collection.insert_one(doc)
        logger.info(
            "Feedback recorded in MongoDB",
            feedback_id=doc["_id"],
            campaign_id=doc["campaign_id"],
            rating=doc["rating"],
        )
        return FeedbackInDB(**doc)

    async def get_by_content(self, content_id: str) -> list[FeedbackInDB]:
        """Fetch all feedback records for a specific asset content ID."""
        cursor = self.collection.find({"content_id": content_id}).sort("created_at", -1)
        items: list[FeedbackInDB] = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            items.append(FeedbackInDB(**doc))
        return items

    async def get_by_campaign(self, campaign_id: str) -> list[FeedbackInDB]:
        """Fetch all feedback records for a campaign."""
        cursor = self.collection.find({"campaign_id": campaign_id}).sort("created_at", -1)
        items: list[FeedbackInDB] = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            items.append(FeedbackInDB(**doc))
        return items

    async def get_average_rating(
        self, campaign_id: str, content_type: Optional[str] = None
    ) -> Optional[float]:
        """Calculate the average rating score for a campaign (optionally filtered by content type)."""
        match_stage: dict = {"campaign_id": campaign_id}
        if content_type:
            match_stage["content_type"] = content_type

        pipeline = [
            {"$match": match_stage},
            {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}}},
        ]
        cursor = self.collection.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        if result and len(result) > 0 and "avg_rating" in result[0]:
            return round(float(result[0]["avg_rating"]), 2)
        return None
