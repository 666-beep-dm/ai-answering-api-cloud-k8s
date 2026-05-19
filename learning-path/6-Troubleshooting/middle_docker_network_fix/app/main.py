"""
app/main.py
Application entry-point.

Bug vs Fix summary
------------------
BUG  scenario: DB_HOST=localhost in .env
     → "Name or service not known" or "Connection refused"
     → GET /health/db returns 503

FIX  scenario: DB_HOST=db in .env  +  healthcheck + depends_on in compose
     → connection succeeds once PostgreSQL is ready
     → GET /health/db returns 200 {"status":"healthy", ...}
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.health import router as health_router

setup_logging()
logger = logging.getLogger("main")


# ── Lifespan ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("🚀  FastAPI Docker Network Debug Stand starting up")
    logger.info("    APP_ENV  : %s", settings.APP_ENV)
    logger.info("    DB_HOST  : %s  ← check this value!", settings.DB_HOST)
    logger.info("    DB_PORT  : %s", settings.DB_PORT)
    logger.info("    DB_NAME  : %s", settings.DB_NAME)
    logger.info("    DB URL   : %s", settings.database_url_safe)
    if settings.DB_HOST == "localhost":
        logger.warning(
            "⚠️  DB_HOST=localhost detected inside Docker! "
            "This will cause 'Connection refused' or 'Name or service not known'. "
            "Set DB_HOST=db (the Docker service name) to fix."
        )
    logger.info("=" * 60)
    yield
    logger.info("🛑  Application shutting down")


# ── App factory ────────────────────────────────────────────────────────────
app = FastAPI(
    title="Docker Network Debug Stand",
    description=(
        "Middle-level debug stand: reproduces and fixes the classic "
        "FastAPI → PostgreSQL 'Connection Refused' error in Docker."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ── Global exception handler ───────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception | type=%s | msg=%s | method=%s | path=%s",
        type(exc).__name__,
        str(exc),
        request.method,
        request.url.path,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": type(exc).__name__,
            "detail": str(exc),
        },
    )


# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(health_router)


# ── Root ───────────────────────────────────────────────────────────────────
@app.get("/", tags=["meta"], summary="Root")
async def root():
    return {
        "project": "Docker Network Debug Stand",
        "docs": "/docs",
        "health": "/health",
        "db_health": "/health/db",
        "db_host_configured": settings.DB_HOST,
    }
