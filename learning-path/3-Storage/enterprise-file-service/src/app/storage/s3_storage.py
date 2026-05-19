"""
Storage layer — S3-compatible client with retry logic.
Uses aioboto3 for async I/O.
"""
from __future__ import annotations
import asyncio
import uuid
import aioboto3
import magic
from botocore.exceptions import ClientError, NoCredentialsError

from app.core.config import BaseConfig
from app.core.exceptions import (
    S3AuthError, S3UploadError, BucketUnavailableError, StorageKeyNotFoundError
)
from app.core.logging import get_logger

log = get_logger(__name__)


class S3Storage:
    def __init__(self, cfg: BaseConfig) -> None:
        self._cfg = cfg
        self._session = aioboto3.Session(
            aws_access_key_id=cfg.s3_access_key,
            aws_secret_access_key=cfg.s3_secret_key,
            region_name=cfg.s3_region,
        )

    def _client(self):
        return self._session.client("s3", endpoint_url=self._cfg.s3_endpoint_url)

    async def _with_retry(self, coro_fn, *args, **kwargs):
        """Execute *coro_fn* with exponential back-off retry."""
        attempts = self._cfg.s3_retry_attempts
        wait = self._cfg.s3_retry_wait_seconds
        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                return await coro_fn(*args, **kwargs)
            except (ClientError, ConnectionError) as exc:
                last_exc = exc
                log.warning("S3 attempt %d/%d failed: %s", attempt, attempts, exc)
                if attempt < attempts:
                    await asyncio.sleep(wait * (2 ** (attempt - 1)))
        raise last_exc

    # ── Bucket ────────────────────────────────────────────────────────────────

    async def ensure_bucket(self, client) -> None:
        try:
            await client.head_bucket(Bucket=self._cfg.s3_bucket_name)
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in ("403", "AuthFailure", "InvalidAccessKeyId", "SignatureDoesNotMatch"):
                raise S3AuthError()
            raise BucketUnavailableError(self._cfg.s3_bucket_name)
        except NoCredentialsError:
            raise S3AuthError(detail="No S3 credentials provided.")

    # ── Upload ────────────────────────────────────────────────────────────────

    async def upload_bytes(self, content: bytes, original_filename: str) -> dict:
        """Upload raw bytes; returns storage metadata dict."""
        cfg = self._cfg
        max_bytes = cfg.max_file_size_mb * 1024 * 1024

        if len(content) > max_bytes:
            from app.core.exceptions import FileTooLargeError
            raise FileTooLargeError(cfg.max_file_size_mb)

        try:
            mime = magic.from_buffer(content, mime=True)
        except Exception:
            mime = "application/octet-stream"

        if mime not in cfg.allowed_mime_types:
            from app.core.exceptions import InvalidMimeTypeError
            raise InvalidMimeTypeError(mime, cfg.allowed_mime_types)

        ext = original_filename.rsplit(".", 1)[-1] if "." in original_filename else ""
        s3_key = f"{uuid.uuid4().hex}_{original_filename}"

        async def _do_upload(client):
            await self.ensure_bucket(client)
            try:
                await client.put_object(
                    Bucket=cfg.s3_bucket_name,
                    Key=s3_key,
                    Body=content,
                    ContentType=mime,
                )
            except ClientError as exc:
                log.error("put_object failed: %s", exc)
                raise S3UploadError(str(exc))

        async with self._client() as client:
            await self._with_retry(_do_upload, client)

        log.info("Uploaded '%s' → s3://%s/%s (%d bytes)", original_filename, cfg.s3_bucket_name, s3_key, len(content))
        return {"s3_key": s3_key, "mime_type": mime, "size_bytes": len(content)}

    # ── Presigned URLs ────────────────────────────────────────────────────────

    async def generate_presigned_upload_url(self, s3_key: str) -> str:
        """Return a PUT presigned URL (client uploads directly to S3)."""
        async with self._client() as client:
            await self.ensure_bucket(client)
            url = await client.generate_presigned_url(
                "put_object",
                Params={"Bucket": self._cfg.s3_bucket_name, "Key": s3_key},
                ExpiresIn=self._cfg.presigned_upload_ttl,
            )
        log.info("Presigned UPLOAD URL generated for key '%s'", s3_key)
        return url

    async def generate_presigned_download_url(self, s3_key: str) -> str:
        """Return a GET presigned URL."""
        async def _do(client):
            try:
                await client.head_object(Bucket=self._cfg.s3_bucket_name, Key=s3_key)
            except ClientError as exc:
                if exc.response["Error"]["Code"] == "404":
                    raise StorageKeyNotFoundError(s3_key)
                raise BucketUnavailableError(self._cfg.s3_bucket_name)
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._cfg.s3_bucket_name, "Key": s3_key},
                ExpiresIn=self._cfg.presigned_download_ttl,
            )

        async with self._client() as client:
            url = await self._with_retry(_do, client)
        log.info("Presigned DOWNLOAD URL generated for key '%s'", s3_key)
        return url
