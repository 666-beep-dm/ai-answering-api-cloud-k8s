"""Async S3 storage layer with exponential retry."""
import asyncio
from typing import Protocol

import aioboto3
from botocore.exceptions import BotoCoreError, ClientError

from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)
_s = get_settings()
_SESSION = aioboto3.Session(
    aws_access_key_id=_s.s3_access_key_id,
    aws_secret_access_key=_s.s3_secret_access_key,
    region_name=_s.s3_region,
)


def _client_kwargs() -> dict:
    return {"endpoint_url": _s.s3_endpoint_url} if _s.s3_endpoint_url else {}


async def _retry(fn, *a, retries: int = 3, base: float = 1.0, **kw):
    last = None
    for i in range(1, retries + 1):
        try:
            return await fn(*a, **kw)
        except (BotoCoreError, ClientError) as e:
            last = e
            await asyncio.sleep(base * 2 ** (i - 1))
    raise last  # type: ignore


async def upload(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    async def _do():
        async with _SESSION.client("s3", **_client_kwargs()) as s3:
            await s3.put_object(Bucket=_s.s3_bucket_name, Key=key, Body=data, ContentType=content_type)
        logger.info(f"S3 upload ok: {key}")
        return key
    return await _retry(_do)


async def health_check() -> bool:
    try:
        async with _SESSION.client("s3", **_client_kwargs()) as s3:
            await s3.head_bucket(Bucket=_s.s3_bucket_name)
        return True
    except Exception as e:
        logger.error(f"S3 health-check failed: {e}")
        return False
