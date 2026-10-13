from datetime import datetime
from typing import Any, Optional, Union
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
import structlog

from backend.models.ad_copy import AdCopyInDB

logger = structlog.get_logger(__name__)


def _query_by_id(id_val: str) -> dict:
    if ObjectId.is_valid(id_val):
        return {"$or": [{"_id": ObjectId(id_val)}, {"_id": id_val}]}
    return {"_id": id_val}


class AdRepository:
    """MongoDB repository for storing and managing generated ad copies."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db.ad_copies

    async def create(self, ad_copy_data: Union[AdCopyInDB, dict[str, Any]]) -> AdCopyInDB:
        """Create a new ad copy document in MongoDB."""
        now = datetime.utcnow()
        if isinstance(ad_copy_data, AdCopyInDB):
            doc = ad_copy_data.model_dump(by_alias=True)
        else:
            doc = dict(ad_copy_data)

        if "_id" not in doc or not doc["_id"]:
            doc["_id"] = str(ObjectId())
        else:
            doc["_id"] = str(doc["_id"])

        doc.setdefault("created_at", now)
        doc.setdefault("updated_at", now)

        # Convert variations to serializable dicts if they are models
        if "variations" in doc and doc["variations"]:
            doc["variations"] = [
                v.model_dump() if hasattr(v, "model_dump") else v
                for v in doc["variations"]
            ]

        await self.collection.insert_one(doc)
        logger.info("Ad copy saved to MongoDB", ad_id=doc["_id"], campaign_id=doc.get("campaign_id"))
        return AdCopyInDB(**doc)

    async def get_by_id(self, ad_id: str) -> Optional[AdCopyInDB]:
        """Retrieve an ad copy document by its ID."""
        doc = await self.collection.find_one(_query_by_id(ad_id))
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return AdCopyInDB(**doc)

    async def get_by_campaign(self, campaign_id: str) -> list[AdCopyInDB]:
        """Fetch all ad copy variations for a specific campaign, ordered newest first."""
        cursor = self.collection.find({"campaign_id": campaign_id}).sort("created_at", -1)
        results: list[AdCopyInDB] = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(AdCopyInDB(**doc))
        return results

    async def delete(self, ad_id: str) -> bool:
        """Delete an ad copy document by ID."""
        res = await self.collection.delete_one(_query_by_id(ad_id))
        deleted = res.deleted_count > 0
        if deleted:
            logger.info("Ad copy deleted", ad_id=ad_id)
        return deleted
