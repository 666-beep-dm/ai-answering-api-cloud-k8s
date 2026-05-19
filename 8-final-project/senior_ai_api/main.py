"""Application entry point — lifespan, middleware, router mount."""
import time, uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.config import get_settings
from core.logging import configure_logging, get_logger, trace_id_var
from core.metrics import http_request_duration_seconds, http_requests_total, metrics_response
from domain.services.rag_service import load_embedder
from infrastructure.cache.redis_client import init_redis, close_redis
from infrastructure.db.engine import close_engine
from infrastructure.vector.qdrant_store import init_qdrant, close_qdrant
from interfaces.api.v1.upload_router import router as upload_router
from interfaces.api.v1.ask_router import router as ask_router
from interfaces.api.v1.health_router import router as health_router

_s = get_settings()
configure_logging(_s.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Startup: initialising dependencies…")
    await init_redis()
    await init_qdrant()
    load_embedder()
    logger.info("All dependencies ready.")
    yield
    # ── Graceful shutdown ─────────────────────────────────────────────────────
    logger.info("Shutdown: closing connections…")
    await close_redis()
    await close_qdrant()
    await close_engine()
    logger.info("Goodbye.")


app = FastAPI(
    title="Scalable AI Answering API",
    description="Enterprise RAG microservice — Clean Architecture · SSE streaming.",
    version="3.0.0",
    lifespan=lifespan,
)


# ── Trace ID + metrics middleware ─────────────────────────────────────────────
@app.middleware("http")
async def observability(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
    trace_id_var.set(trace_id)

    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(f"Unhandled: {exc}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    elapsed = time.perf_counter() - start
    path = request.url.path
    http_requests_total.labels(request.method, path, str(response.status_code)).inc()
    http_request_duration_seconds.labels(request.method, path).observe(elapsed)
    response.headers["X-Trace-ID"] = trace_id
    return response


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(upload_router, prefix="/api/v1/upload", tags=["upload"])
app.include_router(ask_router, prefix="/api/v1/ask", tags=["ask"])
app.include_router(health_router, prefix="/api/v1/health", tags=["health"])


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    return metrics_response()
