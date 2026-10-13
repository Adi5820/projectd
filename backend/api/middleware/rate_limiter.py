from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
import structlog

from backend.api.middleware.request_id import get_request_id
from backend.config import settings

logger = structlog.get_logger(__name__)

# Initialize SlowAPI Limiter using client IP
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.MAX_GENERATIONS_PER_HOUR}/hour"],
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for RateLimitExceeded exceptions, returning structured JSON."""
    req_id = getattr(request.state, "request_id", get_request_id())
    logger.warning("Rate limit exceeded", client=request.client.host if request.client else "unknown", request_id=req_id)
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": f"Too many generation requests. Max {settings.MAX_GENERATIONS_PER_HOUR} per hour.",
            "request_id": req_id,
        },
        headers={"X-Request-ID": req_id, "Retry-After": "3600"},
    )
