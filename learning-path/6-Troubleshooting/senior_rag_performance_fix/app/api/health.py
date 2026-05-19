"""
app/api/health.py
Liveness + readiness probes.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from app.core.config import settings

logger = logging.getLogger("api.health")
router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def liveness():
    logger.info("GET /health")
    return {"status": "ok", "env": settings.APP_ENV}


@router.get("/health/ready", summary="Readiness probe")
async def readiness():
    """Confirms vector store corpus is loaded."""
    from app.core.vector_store import _CORPUS_VECTORS
    return {
        "status": "ready",
        "corpus_size": len(_CORPUS_VECTORS),
        "vector_dim": settings.VECTOR_DIM,
    }
