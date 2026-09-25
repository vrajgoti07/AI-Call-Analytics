"""
AI Call Analytics — Security & Request Correlation Middleware.
"""

from __future__ import annotations

import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("backend.app.core.middleware")


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """
    Assigns or preserves X-Request-ID for every incoming request, logs timing,
    and returns X-Request-ID header in response.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Request-ID"] = request_id

        # Observability: Structured access logging
        logger.info(
            "%s %s %d - %.2fms [request_id=%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies standard HTTP security headers to all responses.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
