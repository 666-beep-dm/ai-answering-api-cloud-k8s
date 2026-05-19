"""GET /api/v1/health — dependency health-checks."""
from fastapi import APIRouter

from infrastructure.cache.redis_client import health_check as redis_hc
from infrastructure.db.engine import engine
from infrastructure.storage.s3_storage import health_check as s3_hc
from infrastructure.vector.qdrant_store import health_check as qdrant_hc
from interfaces.api.v1.schemas import HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    from sqlalchemy import text
    pg_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        pg_ok = True
    except Exception:
        pass

    redis_ok = await redis_hc()
    s3_ok = await s3_hc()
    qdrant_ok = await qdrant_hc()

    overall = "ok" if all([pg_ok, redis_ok, s3_ok, qdrant_ok]) else "degraded"
    return HealthResponse(
        status=overall, postgres=pg_ok, redis=redis_ok, s3=s3_ok, vector_db=qdrant_ok
    )
