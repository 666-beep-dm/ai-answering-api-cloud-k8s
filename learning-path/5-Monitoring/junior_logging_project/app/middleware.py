import logging
import time
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ── Logger setup ───────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("app.middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Intercepts every HTTP request and logs:
      - method + path
      - start time, end time, duration (ms)
      - HTTP status code
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        method = request.method
        path   = request.url.path

        start_ts = time.time()
        logger.info("→ REQUEST   %s %s", method, path)

        try:
            response: Response = await call_next(request)
        except Exception as exc:          # noqa: BLE001
            end_ts   = time.time()
            duration = (end_ts - start_ts) * 1000
            logger.error(
                "← RESPONSE  %s %s | status=500 | %.2f ms | error=%s",
                method, path, duration, exc,
            )
            raise

        end_ts   = time.time()
        duration = (end_ts - start_ts) * 1000

        logger.info(
            "← RESPONSE  %s %s | status=%s | %.2f ms",
            method, path, response.status_code, duration,
        )
        return response
