"""patched_service/app/main.py — Production-Ready FastAPI RAG-сервис."""

import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Depends, HTTPException, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from .config import get_settings, Settings
from .observability import setup_logging, setup_tracing, trace_id_var, generate_trace_id
from .llm_service import LLMService
from .schemas import QueryRequest, QueryResponse, IngestRequest, HealthResponse
from .metrics import CIRCUIT_BREAKER_STATE

logger = logging.getLogger(__name__)

# ─── Redis connection pool (создаётся один раз) ───────────────────────────────
redis_pool: aioredis.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_pool
    settings = get_settings()
    setup_logging(settings.log_level)
    setup_tracing(settings.otel_exporter_endpoint, settings.otel_service_name)
    logger.info(
        "startup service=%s model=%s key=%s",
        settings.otel_service_name,
        settings.openai_model,
        settings.masked_key(),          # ключ замаскирован!
    )
    redis_pool = aioredis.from_url(settings.redis_url, decode_responses=False)
    yield
    if redis_pool:
        await redis_pool.aclose()
    logger.info("shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="RAG AI Service",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.log_level == "DEBUG" else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    # OBS: Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # ─── Middleware: сквозной Trace-ID ────────────────────────────────────────
    @app.middleware("http")
    async def trace_middleware(request: Request, call_next):
        tid = request.headers.get("X-Trace-ID", generate_trace_id())
        token = trace_id_var.set(tid)
        response = await call_next(request)
        response.headers["X-Trace-ID"] = tid
        trace_id_var.reset(token)
        return response

    # ─── Dependencies ─────────────────────────────────────────────────────────
    def get_llm() -> LLMService:
        return LLMService(settings, redis_pool)

    async def verify_token(x_api_token: str = Header(...)) -> None:
        if x_api_token != settings.api_token_secret:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    # ─── Health endpoints (для K8s Liveness/Readiness) ────────────────────────
    @app.get("/health/live", response_model=HealthResponse, tags=["health"])
    async def liveness() -> HealthResponse:
        return HealthResponse(status="ok", service="rag-api")

    @app.get("/health/ready", response_model=HealthResponse, tags=["health"])
    async def readiness() -> HealthResponse:
        try:
            await redis_pool.ping()
        except Exception:
            raise HTTPException(status_code=503, detail="Redis unavailable")
        return HealthResponse(status="ready", service="rag-api")

    # ─── RAG endpoints ────────────────────────────────────────────────────────
    @app.post(
        "/rag/query",
        response_model=QueryResponse,
        dependencies=[Depends(verify_token)],
        tags=["rag"],
    )
    async def rag_query(
        payload: QueryRequest,
        llm: LLMService = Depends(get_llm),
    ) -> QueryResponse:
        tid = trace_id_var.get("")
        logger.info("rag_query trace_id=%s chars=%d", tid, len(payload.query))
        result = await llm.chat(payload.query, trace_id=tid)
        return QueryResponse(**result)

    @app.post(
        "/rag/ingest",
        dependencies=[Depends(verify_token)],
        tags=["rag"],
    )
    async def rag_ingest(payload: IngestRequest) -> dict:
        tid = trace_id_var.get("")
        logger.info("rag_ingest trace_id=%s docs=%d", tid, len(payload.documents))
        # В продакшне: отправить задачу в Celery (асинхронно)
        return {"queued": len(payload.documents), "trace_id": tid}

    return app


app = create_app()
