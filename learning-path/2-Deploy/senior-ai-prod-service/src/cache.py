"""
Semantic cache using Redis.
Key strategy: sha256(question.lower().strip())
For true semantic similarity, embed the question and compare cosine
similarity before writing/reading — stub shown here for extensibility.
"""
import hashlib
import json
import logging
from typing import Any

import redis.asyncio as aioredis

from src.config import get_settings

logger = logging.getLogger(__name__)
_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        s = get_settings()
        _redis_client = await aioredis.from_url(
            s.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


def _cache_key(question: str) -> str:
    normalized = question.lower().strip()
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return f"rag:cache:{digest}"


async def get_cached(question: str) -> dict[str, Any] | None:
    try:
        r = await get_redis()
        raw = await r.get(_cache_key(question))
        if raw:
            logger.info("cache_hit", extra={"question_prefix": question[:60]})
            return json.loads(raw)
    except Exception as exc:
        logger.warning("cache_get_error: %s", exc)
    return None


async def set_cached(question: str, payload: dict[str, Any]) -> None:
    try:
        r = await get_redis()
        ttl = get_settings().cache_ttl_seconds
        await r.setex(_cache_key(question), ttl, json.dumps(payload))
    except Exception as exc:
        logger.warning("cache_set_error: %s", exc)


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
