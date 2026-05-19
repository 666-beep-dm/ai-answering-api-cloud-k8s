"""
Async S3-compatible storage service with exponential-backoff retry logic.
Supports AWS S3, Cloudflare R2, Selectel, MinIO — anything that speaks S3.
"""

import asyncio
import os
from typing import Optional

import aioboto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_SESSION = aioboto3.Session(
    aws_access_key_id=settings.s3_access_key_id,
    aws_secret_access_key=settings.s3_secret_access_key,
    region_name=settings.s3_region,
)

# Retry configuration
_MAX_RETRIES = 3
_BASE_DELAY = 1.0   # seconds


async def _with_retry(coro_fn, *args, **kwargs):
    """Execute an async callable with exponential-backoff retry."""
    last_exc: Optional[Exception] = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return await coro_fn(*args, **kwargs)
        except (BotoCoreError, ClientError) as exc:
            last_exc = exc
            delay = _BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(
                f"S3 operation failed (attempt {attempt}/{_MAX_RETRIES}), "
                f"retrying in {delay}s — {exc}"
            )
            await asyncio.sleep(delay)
    raise last_exc  # type: ignore[misc]


def _client_kwargs() -> dict:
    kwargs: dict = {}
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return kwargs


async def upload_file(file_key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload bytes to S3; return the public object key."""

    async def _upload():
        async with _SESSION.client("s3", **_client_kwargs()) as s3:
            await s3.put_object(
                Bucket=settings.s3_bucket_name,
                Key=file_key,
                Body=data,
                ContentType=content_type,
            )
        logger.info(f"S3 upload ok: s3://{settings.s3_bucket_name}/{file_key}")
        return file_key

    return await _with_retry(_upload)


async def check_connection() -> bool:
    """Return True if we can list the bucket (health-check)."""
    try:
        async with _SESSION.client("s3", **_client_kwargs()) as s3:
            await s3.head_bucket(Bucket=settings.s3_bucket_name)
        return True
    except Exception as exc:
        logger.error(f"S3 health-check failed: {exc}")
        return False
