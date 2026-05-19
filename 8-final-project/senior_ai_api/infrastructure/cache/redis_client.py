"""Async Redis client for session / response caching."""
import json
from typing import Any

import redis.asyncio as aioredis

from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)
_settings = get_settings()
_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    global _redis
    _redis = aioredis.from_url(_settings.redis_url, decode_responses=True)
    logger.info("Redis connection established.")


async def close_redis() -> None:
    if _redis:
        await _redis.aclose()


async def cache_get(key: str) -> Any | None:
    if _redis is None:
        return None
    raw = await _redis.get(key)
    return json.loads(raw) if raw else None


async def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    if _redis is None:
        return
    ttl = ttl or _settings.cache_ttl_seconds
    await _redis.setex(key, ttl, json.dumps(value))


async def health_check() -> bool:
    try:
        return bool(_redis and await _redis.ping())
    except Exception:
        return False
