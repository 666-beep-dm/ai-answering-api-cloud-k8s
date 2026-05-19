"""
RAG API Service — FastAPI + asyncpg (PostgreSQL) + aioredis
"""
import os
import asyncio
import logging
from contextlib import asynccontextmanager

import asyncpg
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger("rag_api")
logging.basicConfig(level=logging.INFO)

# ── Config from environment ──────────────────────────────────────────────────
DB_DSN = (
    f"postgresql://{os.environ['PG_USER']}:{os.environ['PG_PASSWORD']}"
    f"@{os.environ.get('PG_HOST', 'postgres-svc')}:"
    f"{os.environ.get('PG_PORT', '5432')}/{os.environ['PG_DB']}"
)
REDIS_URL  = os.environ.get("REDIS_URL", "redis://:password@redis-svc:6379/0")
APP_ENV    = os.environ.get("APP_ENV", "production")
CACHE_TTL  = int(os.environ.get("CACHE_TTL_SECONDS", "60"))

# ── App state ────────────────────────────────────────────────────────────────
class AppState:
    db_pool:    asyncpg.Pool | None = None
    redis:      aioredis.Redis | None = None

state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown resource management."""
    logger.info("Connecting to PostgreSQL...")
    state.db_pool = await asyncpg.create_pool(
        dsn=DB_DSN, min_size=2, max_size=10, command_timeout=30
    )
    logger.info("Connecting to Redis...")
    state.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)

    # Ensure schema exists
    async with state.db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS rag_history (
                id        SERIAL PRIMARY KEY,
                question  TEXT NOT NULL,
                answer    TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

    yield  # ── application runs here ──

    logger.info("Closing connections...")
    if state.redis:
        await state.redis.aclose()
    if state.db_pool:
        await state.db_pool.close()


app = FastAPI(title="RAG API", version="1.0.0", lifespan=lifespan)


# ── Schemas ───────────────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer:   str
    cached:   bool
    question: str


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health", tags=["ops"])
async def health():
    """Liveness / readiness probe endpoint."""
    checks: dict[str, str] = {"api": "ok"}

    try:
        async with state.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"

    try:
        await state.redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ok" if all_ok else "degraded", "checks": checks, "env": APP_ENV}


@app.post("/ask", response_model=AskResponse, tags=["rag"])
async def ask(body: AskRequest):
    """RAG query endpoint with Redis caching and Postgres persistence."""
    if not body.question.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty question")

    cache_key = f"rag:answer:{hash(body.question)}"

    # 1. Check cache
    cached = await state.redis.get(cache_key)
    if cached:
        return AskResponse(question=body.question, answer=cached, cached=True)

    # 2. Stub RAG logic — replace with real LLM call
    answer = f"[RAG] Answer for: '{body.question}' (env={APP_ENV})"

    # 3. Persist to Postgres
    async with state.db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO rag_history (question, answer) VALUES ($1, $2)",
            body.question, answer
        )

    # 4. Cache result
    await state.redis.setex(cache_key, CACHE_TTL, answer)

    return AskResponse(question=body.question, answer=answer, cached=False)
