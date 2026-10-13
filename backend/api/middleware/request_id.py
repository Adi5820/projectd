import uuid
from contextvars import ContextVar
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

# Context variable storing the current request ID
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Retrieve current request ID from context variable."""
    return request_id_ctx_var.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns or preserves a unique X-Request-ID for every HTTP request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if caller supplied an X-Request-ID header
        req_id = request.headers.get("X-Request-ID")
        if not req_id:
            req_id = str(uuid.uuid4())

        # Bind to contextvar and request state
        token = request_id_ctx_var.set(req_id)
        request.state.request_id = req_id

        # Bind request_id to structlog context
        structlog.contextvars.bind_contextvars(request_id=req_id)

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
            request_id_ctx_var.reset(token)
