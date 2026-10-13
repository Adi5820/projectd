from datetime import datetime
from typing import Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
import structlog

from backend.models.campaign import CampaignCreate, CampaignInDB, CampaignStatus

logger = structlog.get_logger(__name__)


def _query_by_id(id_val: str) -> dict:
    if ObjectId.is_valid(id_val):
        return {"$or": [{"_id": ObjectId(id_val)}, {"_id": id_val}]}
    return {"_id": id_val}


class CampaignRepository:
    """MongoDB repository for managing ad campaigns."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db.campaigns

    async def create(self, campaign: CampaignCreate) -> CampaignInDB:
        """Create a new campaign document."""
        now = datetime.utcnow()
        doc = campaign.model_dump()
        doc.update({
            "_id": str(ObjectId()),
            "status": CampaignStatus.DRAFT.value,
            "created_at": now,
            "updated_at": now,
        })
        await self.collection.insert_one(doc)
        logger.info("Campaign created in MongoDB", campaign_id=doc["_id"])
        return CampaignInDB(**doc)

    async def get_by_id(self, campaign_id: str) -> Optional[CampaignInDB]:
        """Fetch a campaign by its ID."""
        doc = await self.collection.find_one(_query_by_id(campaign_id))
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return CampaignInDB(**doc)

    async def list_all(
        self, skip: int = 0, limit: int = 20, status: Optional[CampaignStatus] = None
    ) -> tuple[list[CampaignInDB], int]:
        """List campaigns with pagination and optional status filter, returning (items, total_count)."""
        query: dict = {}
        if status:
            query["status"] = status.value

        total = await self.collection.count_documents(query)
        cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        items: list[CampaignInDB] = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            items.append(CampaignInDB(**doc))

        return items, total

    async def update_status(self, campaign_id: str, status: CampaignStatus) -> Optional[CampaignInDB]:
        """Update the status of an existing campaign."""
        now = datetime.utcnow()
        updated_doc = await self.collection.find_one_and_update(
            _query_by_id(campaign_id),
            {"$set": {"status": status.value, "updated_at": now}},
            return_document=True,
        )
        if not updated_doc:
            return None
        updated_doc["_id"] = str(updated_doc["_id"])
        logger.info("Updated campaign status", campaign_id=campaign_id, status=status.value)
        return CampaignInDB(**updated_doc)

    async def delete(self, campaign_id: str) -> bool:
        """Delete a campaign document by its ID."""
        res = await self.collection.delete_one(_query_by_id(campaign_id))
        deleted = res.deleted_count > 0
        if deleted:
            logger.info("Campaign deleted", campaign_id=campaign_id)
        return deleted
