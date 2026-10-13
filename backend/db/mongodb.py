import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from backend.config import settings

logger = structlog.get_logger(__name__)


class MongoDBManager:
    """Manages the MongoDB connection lifecycle and index initialization using Motor."""

    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self.db: AsyncIOMotorDatabase | None = None

    async def connect(self) -> None:
        """Connect to MongoDB server using the configured URL and database name."""
        try:
            logger.info("Connecting to MongoDB", url=settings.MONGODB_URL, db=settings.MONGODB_DB_NAME)
            self.client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
            self.db = self.client[settings.MONGODB_DB_NAME]
            # Verify connectivity with ping
            await self.client.admin.command("ping")
            logger.info("Successfully connected to MongoDB", db=settings.MONGODB_DB_NAME)
        except Exception as exc:
            logger.error("Failed to connect to MongoDB", error=str(exc))
            # Keep client and db assigned so subsequent retries or graceful degradation are possible
            raise

    async def disconnect(self) -> None:
        """Close the MongoDB client connection."""
        if self.client is not None:
            logger.info("Closing MongoDB connection")
            self.client.close()
            self.client = None
            self.db = None
            logger.info("MongoDB connection closed")

    async def create_indexes(self) -> None:
        """Create required indexes for all application collections."""
        if self.db is None:
            logger.warning("Cannot create indexes: database connection is not initialized")
            return

        try:
            # campaigns: created_at, status
            await self.db.campaigns.create_index([("created_at", DESCENDING)], background=True)
            await self.db.campaigns.create_index([("status", ASCENDING)], background=True)

            # jobs: campaign_id, status
            await self.db.jobs.create_index([("campaign_id", ASCENDING)], background=True)
            await self.db.jobs.create_index([("status", ASCENDING)], background=True)

            # ad_copies: campaign_id
            await self.db.ad_copies.create_index([("campaign_id", ASCENDING)], background=True)

            # posters: campaign_id
            await self.db.posters.create_index([("campaign_id", ASCENDING)], background=True)

            # videos: campaign_id
            await self.db.videos.create_index([("campaign_id", ASCENDING)], background=True)

            # feedback: campaign_id, content_id
            await self.db.feedback.create_index([("campaign_id", ASCENDING)], background=True)
            await self.db.feedback.create_index([("content_id", ASCENDING)], background=True)
            await self.db.feedback.create_index(
                [("campaign_id", ASCENDING), ("content_id", ASCENDING)],
                background=True,
            )

            logger.info("Successfully created/verified MongoDB indexes")
        except Exception as exc:
            logger.error("Error creating MongoDB indexes", error=str(exc))
            raise

    async def health_check(self) -> bool:
        """Check if MongoDB server is responsive."""
        if self.client is None:
            return False
        try:
            await self.client.admin.command("ping")
            return True
        except Exception as exc:
            logger.warning("MongoDB health check failed", error=str(exc))
            return False

    def get_database(self) -> AsyncIOMotorDatabase:
        """Return the active database instance, raising RuntimeError if not connected."""
        if self.db is None:
            raise RuntimeError("Database is not connected. Call connect() first.")
        return self.db


# Global manager and database accessor
mongodb_manager = MongoDBManager()


def get_database() -> AsyncIOMotorDatabase:
    """Convenience function to get the current database instance."""
    return mongodb_manager.get_database()


# Alias for compatibility
db = mongodb_manager
