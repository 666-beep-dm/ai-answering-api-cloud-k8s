"""
app/api/health.py
Health-check endpoints:
  GET /health      → basic liveness probe
  GET /health/db   → database connectivity probe (SELECT 1)
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.database import check_db_connection
from app.core.config import settings

logger = logging.getLogger("api.health")
router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="Liveness probe")
async def liveness():
    """Returns 200 if the application process is running."""
    logger.info("GET /health called | env=%s", settings.APP_ENV)
    return {"status": "ok", "env": settings.APP_ENV}


@router.get("/db", summary="Database connectivity probe")
async def db_health():
    """
    Executes SELECT 1 against PostgreSQL and returns connection status.

    * **200 OK**         → database is reachable and responding
    * **503 Unavailable** → cannot connect (wrong host, DB not ready, etc.)

    Check server logs for detailed connection lifecycle messages.
    """
    logger.info("GET /health/db called | db_host=%s", settings.DB_HOST)
    result = await check_db_connection()

    if result["status"] == "healthy":
        logger.info("GET /health/db → healthy")
        return JSONResponse(status_code=200, content=result)
    else:
        logger.error("GET /health/db → unhealthy | error=%s", result.get("error"))
        return JSONResponse(status_code=503, content=result)
