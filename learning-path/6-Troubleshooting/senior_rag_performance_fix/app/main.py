"""
app/main.py
FastAPI application entry-point.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.profiler.middleware import RequestTimingMiddleware
from app.api.rag import router as rag_router
from app.api.health import router as health_router

setup_logging()
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 70)
    logger.info("🚀  Senior RAG Performance Diagnostic Stand — startup")
    logger.info("    APP_ENV        : %s", settings.APP_ENV)
    logger.info("    BLOCKING_IO_S  : %.1f  (simulated retrieval delay)", settings.SIMULATE_BLOCKING_IO_SECONDS)
    logger.info("    LLM_DELAY_S    : %.1f  (simulated LLM latency)", settings.SIMULATE_LLM_DELAY_SECONDS)
    logger.info("    CORPUS_SIZE    : %d vectors", settings.VECTOR_CORPUS_SIZE)
    logger.info("    Endpoints:")
    logger.info("      POST /ask            ❌ buggy  (blocks event loop)")
    logger.info("      POST /ask-optimized  ✅ fixed  (fully async)")
    logger.info("      POST /ask-stream     ✅ stream (SSE, TTFT ~200ms)")
    logger.info("=" * 70)
    yield
    logger.info("🛑  Application shutting down")


app = FastAPI(
    title="Senior RAG Performance Diagnostic Stand",
    description=(
        "Reproduces and fixes three Senior-level RAG bottlenecks:\n\n"
        "1. **Blocking I/O** — `time.sleep` stalls the event loop\n"
        "2. **LLM Timeout** — no-timeout sync call hangs workers\n"
        "3. **Nginx misconfiguration** — 5s `proxy_read_timeout` → 504\n\n"
        "Compare `/ask` (❌ buggy) vs `/ask-optimized` / `/ask-stream` (✅ fixed)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────
app.add_middleware(RequestTimingMiddleware)

# ── Exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception | type=%s | msg=%s | path=%s",
        type(exc).__name__, str(exc), request.url.path,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"error": type(exc).__name__, "detail": str(exc)},
    )

# ── Routers ────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(rag_router)

@app.get("/", tags=["meta"])
async def root():
    return {
        "project": "Senior RAG Performance Diagnostic Stand",
        "docs": "/docs",
        "endpoints": {
            "buggy": "POST /ask",
            "optimized": "POST /ask-optimized",
            "streaming": "POST /ask-stream",
        },
    }
