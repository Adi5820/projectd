from backend.api.routes.ads import router as ads_router
from backend.api.routes.campaigns import router as campaigns_router
from backend.api.routes.feedback import router as feedback_router
from backend.api.routes.generate import router as generate_router
from backend.api.routes.health import router as health_router
from backend.api.routes.jobs import router as jobs_router
from backend.api.routes.posters import router as posters_router
from backend.api.routes.rag import documents_router, router as rag_router
from backend.api.routes.videos import router as videos_router

__all__ = [
    "campaigns_router",
    "ads_router",
    "posters_router",
    "videos_router",
    "rag_router",
    "documents_router",
    "jobs_router",
    "feedback_router",
    "health_router",
    "generate_router",
]
