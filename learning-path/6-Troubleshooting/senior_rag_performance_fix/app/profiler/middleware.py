"""
app/profiler/middleware.py
Request-level timing middleware — logs JSON metrics for every request.
Non-blocking: uses time.perf_counter(), no disk I/O in hot path.
"""
from __future__ import annotations

import json
import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("profiler.middleware")


class RequestTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1_000

        metric = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        }
        logger.info("request_metric | %s", json.dumps(metric))
        return response
