from __future__ import annotations

import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import get_logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestTimingMiddleware(BaseHTTPMiddleware):
    _SKIP_PATHS = {"/health/", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        rid = getattr(request.state, "request_id", None)
        logger = get_logger("http", rid)

        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.log_error_with_context(
                "request_failed", error=exc,
                method=request.method, path=request.url.path, duration_ms=f"{elapsed:.2f}",
            )
            raise

        elapsed = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time"] = f"{elapsed:.2f}ms"

        if request.url.path not in self._SKIP_PATHS:
            logger.log_performance(
                "http_request", elapsed,
                method=request.method, path=request.url.path, status=response.status_code,
            )
        return response
