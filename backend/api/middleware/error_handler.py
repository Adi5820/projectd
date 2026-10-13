from typing import Callable
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import structlog

from backend.api.middleware.request_id import get_request_id

logger = structlog.get_logger(__name__)


class GlobalExceptionMiddleware(BaseHTTPMiddleware):
    """Catches all unhandled exceptions occurring in the request lifecycle and returns standardized JSON."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except StarletteHTTPException as exc:
            req_id = getattr(request.state, "request_id", get_request_id())
            logger.warning(
                "HTTPException handled",
                status_code=exc.status_code,
                detail=exc.detail,
                request_id=req_id,
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": "HTTP Exception",
                    "detail": exc.detail,
                    "request_id": req_id,
                },
                headers={"X-Request-ID": req_id},
            )
        except Exception as exc:
            req_id = getattr(request.state, "request_id", get_request_id())
            logger.error(
                "Unhandled server exception intercepted",
                error=str(exc),
                exc_info=True,
                request_id=req_id,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": str(exc),
                    "request_id": req_id,
                },
                headers={"X-Request-ID": req_id},
            )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """FastAPI global fallback exception handler."""
    req_id = getattr(request.state, "request_id", get_request_id())
    logger.error(
        "Global exception handled by FastAPI handler",
        error=str(exc),
        exc_info=True,
        request_id=req_id,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
            "request_id": req_id,
        },
        headers={"X-Request-ID": req_id},
    )
