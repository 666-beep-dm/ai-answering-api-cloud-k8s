from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.routers.files import router as files_router

setup_logging()
cfg = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── startup ──────────────────────────────────────────────────────────────
    yield
    # ── shutdown ─────────────────────────────────────────────────────────────


app = FastAPI(
    title=cfg.app_name,
    version=cfg.app_version,
    description=(
        "Enterprise-grade async file management microservice. "
        "Supports direct server uploads, presigned S3 URLs, "
        "PostgreSQL metadata persistence, and Redis caching."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "version": cfg.app_version, "env": cfg.environment}
