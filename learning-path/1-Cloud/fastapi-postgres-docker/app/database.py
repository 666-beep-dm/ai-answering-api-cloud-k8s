"""
Database layer — async SQLAlchemy 2.0 + asyncpg driver.
Connection URL is read exclusively from DATABASE_URL env variable.
"""

import os
from typing import Tuple

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import text

# ── Engine ────────────────────────────────────────────────────────
DATABASE_URL: str = os.environ["DATABASE_URL"]

# asyncpg requires postgresql+asyncpg:// scheme
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,   # reconnect on stale connections
    echo=False,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base model ────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency (use in route handlers) ───────────────────────────
async def get_db() -> AsyncSession:  # type: ignore[return]
    async with AsyncSessionLocal() as session:
        yield session


# ── Health probe ─────────────────────────────────────────────────
async def check_db_connection() -> Tuple[bool, str]:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
