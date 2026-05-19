"""
app/core/database.py

SQLAlchemy 2.0 async engine + session factory.

Connection flow with detailed logging so Junior/Middle developers
can clearly see what happens at each stage.
"""

import logging

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger("db")

# ── Engine ─────────────────────────────────────────────────────────────────
# pool_pre_ping=True: SQLAlchemy will issue a lightweight SELECT before
# handing a connection from the pool, recycling stale connections gracefully.
engine: AsyncEngine = create_async_engine(
    settings.async_database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={
        "server_settings": {"application_name": "fastapi_debug_stand"},
    },
)

# ── Session factory ────────────────────────────────────────────────────────
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Dependency ─────────────────────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Health probe ───────────────────────────────────────────────────────────
async def check_db_connection() -> dict:
    """
    Execute SELECT 1 against the database and return a structured result.
    Used by GET /health/db.

    Logs each stage so the developer can trace the connection lifecycle:
      1. Attempting connection  → shows resolved URL (password redacted)
      2. Query issued           → confirms the TCP handshake succeeded
      3. Result received        → confirms the query round-trip
      4. Error details          → on failure, logs the exception type + message
    """
    url_safe = settings.database_url_safe
    logger.info("⏳ [DB-HEALTH] Attempting connection | url=%s", url_safe)

    try:
        async with engine.connect() as conn:
            logger.info("✅ [DB-HEALTH] TCP connection established | issuing SELECT 1")
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
            logger.info("✅ [DB-HEALTH] Query round-trip OK | result=%s", value)
            return {
                "status": "healthy",
                "host": settings.DB_HOST,
                "port": settings.DB_PORT,
                "database": settings.DB_NAME,
                "query": "SELECT 1",
                "result": value,
            }
    except Exception as exc:
        logger.error(
            "❌ [DB-HEALTH] Connection FAILED | error_type=%s | message=%s | url=%s",
            type(exc).__name__,
            str(exc),
            url_safe,
            exc_info=True,
        )
        return {
            "status": "unhealthy",
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "database": settings.DB_NAME,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "hint": (
                "If error contains 'Name or service not known' or 'Connection refused', "
                "check that DB_HOST matches the Docker service name (e.g. 'db'), "
                "not 'localhost'."
            ),
        }
