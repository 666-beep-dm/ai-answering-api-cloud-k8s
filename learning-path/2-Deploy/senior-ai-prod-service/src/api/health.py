from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache import get_redis
from src.config import get_settings
from src.db import get_db
from src.schemas import HealthResponse

router = APIRouter(tags=["Ops"])


@router.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)):
    s = get_settings()
    # DB probe
    await db.execute(text("SELECT 1"))
    return HealthResponse(status="ok", version=s.app_version, env=s.app_env)


@router.get("/readiness")
async def readiness(db: AsyncSession = Depends(get_db)):
    """K8s / compose healthcheck endpoint."""
    await db.execute(text("SELECT 1"))
    redis = await get_redis()
    await redis.ping()
    return {"ready": True}
