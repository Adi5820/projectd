from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
import structlog

from backend.api.middleware.error_handler import (
    GlobalExceptionMiddleware,
    global_exception_handler,
)
from backend.api.middleware.rate_limiter import (
    limiter,
    rate_limit_exceeded_handler,
)
from backend.api.middleware.request_id import RequestIDMiddleware
from backend.api.routes import (
    ads_router,
    campaigns_router,
    documents_router,
    feedback_router,
    generate_router,
    health_router,
    jobs_router,
    posters_router,
    rag_router,
    videos_router,
)
from backend.config import settings
from backend.db.mongodb import mongodb_manager

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handles startup and shutdown events: connects to MongoDB and initializes ChromaDB."""
    logger.info("Initializing Agentic Ads API services...")

    # Ensure local media and ChromaDB directories exist
    media_dir = Path(settings.MEDIA_STORAGE_PATH)
    media_dir.mkdir(parents=True, exist_ok=True)

    chroma_dir = Path(settings.CHROMA_PERSIST_DIR)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    # Connect to MongoDB & create indexes
    try:
        await mongodb_manager.connect()
        await mongodb_manager.create_indexes()
        logger.info("MongoDB initialized successfully")
    except Exception as exc:
        logger.error("Could not connect to MongoDB on startup", error=str(exc))

    yield

    # Disconnect from MongoDB on shutdown
    logger.info("Cleaning up Agentic Ads API services...")
    await mongodb_manager.disconnect()


# Instantiate FastAPI application
app = FastAPI(
    title="Agentic Ads API",
    version="1.0.0",
    description="Multi-Agent AI Advertising Platform API for automated copy, poster, and video generation.",
    lifespan=lifespan,
)

# Configure SlowAPI rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Middlewares (executed in reverse order: RequestID -> CORS -> GlobalException)
app.add_middleware(GlobalExceptionMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure media directory exists before mounting static files
media_path = Path(settings.MEDIA_STORAGE_PATH)
media_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_path)), name="media")

# Include all API route modules
app.include_router(health_router)
app.include_router(campaigns_router)
app.include_router(ads_router)
app.include_router(posters_router)
app.include_router(videos_router)
app.include_router(rag_router)
app.include_router(documents_router)
app.include_router(jobs_router)
app.include_router(feedback_router)
app.include_router(generate_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True,
    )
