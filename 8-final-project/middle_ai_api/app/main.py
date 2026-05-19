"""Application entry point — lifespan, middleware, router registration."""

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routers import router
from app.core.logging import get_logger
from app.services.rag_service import init_rag

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: initialise RAG index. Shutdown: nothing to clean up."""
    logger.info("Starting up — loading RAG pipeline...")
    init_rag()
    logger.info("RAG pipeline ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Middle-tier AI Answering API",
    description="RAG-powered Q&A service with S3 storage and GPT-4o-mini.",
    version="2.0.0",
    lifespan=lifespan,
)


# ── Request logging middleware ────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} ({elapsed_ms}ms)"
    )
    return response


# ── Global exception handler ─────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exc_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


app.include_router(router)
