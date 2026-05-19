"""
FastAPI Senior Observability Service — application entry point.
Three Pillars: Metrics (Prometheus) \u00b7 Logs (JSON/Loki) \u00b7 Traces (OTel)
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.observability.logger import logger
from app.observability.metrics import init_metrics
from app.observability.tracer import init_tracer
from app.observability.middleware import ObservabilityMiddleware
from app.observability.alerting import alerting_background_task
from app.api.routes import router

_settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    init_tracer()
    init_metrics()
    asyncio.create_task(alerting_background_task())
    logger.info(
        "Application startup complete",
        extra={"trace_id": "startup", "span_id": "0",
               "request_id": "startup", "path": "-", "method": "-"},
    )
    yield
    logger.info(
        "Application shutting down",
        extra={"trace_id": "shutdown", "span_id": "0",
               "request_id": "shutdown", "path": "-", "method": "-"},
    )


# ── Inner FastAPI (exception handlers + router) ───────────────────────────
_inner = FastAPI(
    title=_settings.app_name,
    version=_settings.app_version,
    description=(
        "Enterprise-grade observability platform: "
        "distributed tracing \u00b7 Prometheus metrics \u00b7 structured JSON logs \u00b7 "
        "sliding-window alerting."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
register_exception_handlers(_inner)
_inner.include_router(router)


# ── ObservabilityMiddleware wraps inner stack directly ────────────────────
# This places us ABOVE ExceptionMiddleware but BELOW ServerErrorMiddleware,
# so FastAPI exception handlers always convert errors to Responses before
# our middleware reads the final status code.
class _App:
    def __init__(self) -> None:
        self._stack: ASGIApp | None = None

    def _build(self) -> ASGIApp:
        if self._stack is None:
            self._stack = ObservabilityMiddleware(_inner)
        return self._stack

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self._build()(scope, receive, send)


app = _App()
