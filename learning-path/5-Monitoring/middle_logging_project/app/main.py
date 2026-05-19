"""
FastAPI Advanced JSON Logging — application entry point.
"""

from fastapi import FastAPI

from app.core.logger_config import logger
from app.core.exception_handlers import register_exception_handlers
from app.middlewares.request_context import RequestContextMiddleware
from app.api.routes import router

app = FastAPI(
    title="FastAPI Advanced JSON Logging",
    description=(
        "Middle-level project: structured JSON logs, request_id tracing, "
        "centralised error handling with stack traces."
    ),
    version="2.0.0",
)

# ── Middleware (outermost first) ───────────────────────────────────────────
app.add_middleware(RequestContextMiddleware)

# ── Exception handlers ────────────────────────────────────────────────────
register_exception_handlers(app)

# ── Routers ───────────────────────────────────────────────────────────────
app.include_router(router)

logger.info("Application startup complete", extra={
    "request_id": "startup", "path": "-", "method": "-",
})
