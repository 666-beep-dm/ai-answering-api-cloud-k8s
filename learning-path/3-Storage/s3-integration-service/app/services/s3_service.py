import uuid
import aioboto3
import magic
from botocore.exceptions import ClientError, NoCredentialsError, EndpointResolutionError
from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import (
    S3AuthError,
    FileTooLargeError,
    BucketUnavailableError,
    FileNotFoundInStorageError,
    InvalidMimeTypeError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class S3Service:
    """
    Encapsulates all async interactions with an S3-compatible object store.
    Uses aioboto3 for non-blocking I/O.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session = aioboto3.Session(
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _client(self):
        """Return a context-managed async S3 client."""
        return self._session.client(
            "s3",
            endpoint_url=self._settings.s3_endpoint_url,
        )

    async def _ensure_bucket(self, client) -> None:
        """Check that the bucket exists and is accessible."""
        try:
            await client.head_bucket(Bucket=self._settings.s3_bucket_name)
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in ("403", "AuthFailure", "InvalidAccessKeyId", "SignatureDoesNotMatch"):
                logger.error("S3 auth error: %s", exc)
                raise S3AuthError()
            logger.error("Bucket unavailable (%s): %s", code, exc)
            raise BucketUnavailableError(self._settings.s3_bucket_name)
        except (NoCredentialsError, EndpointResolutionError) as exc:
            logger.error("S3 connection error: %s", exc)
            raise S3AuthError(detail=str(exc))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def upload_file(self, file: UploadFile) -> dict:
        """
        Validate and upload *file* to S3.

        Validation steps:
        1. Read content into memory (stream-safe for small files ≤ max_mb).
        2. Check size.
        3. Detect MIME type via libmagic for accuracy (falls back to content-type header).
        4. Upload to S3.
        """
        cfg = self._settings
        max_bytes = cfg.max_file_size_mb * 1024 * 1024

        content = await file.read()
        size = len(content)
        logger.info("Received file '%s' — %d bytes", file.filename, size)

        # --- Size check ---
        if size > max_bytes:
            logger.warning("File '%s' rejected: %d bytes > %d bytes limit", file.filename, size, max_bytes)
            raise FileTooLargeError(cfg.max_file_size_mb)

        # --- MIME check (libmagic is more reliable than browser-sent Content-Type) ---
        try:
            detected_mime = magic.from_buffer(content, mime=True)
        except Exception:
            detected_mime = file.content_type or "application/octet-stream"

        if detected_mime not in cfg.allowed_mime_types:
            logger.warning("File '%s' rejected: MIME '%s' not allowed", file.filename, detected_mime)
            raise InvalidMimeTypeError(detected_mime, cfg.allowed_mime_types)

        # --- Generate unique key ---
        ext = file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else ""
        unique_name = f"{uuid.uuid4().hex}_{file.filename}" if file.filename else f"{uuid.uuid4().hex}"
        if ext and not unique_name.endswith(f".{ext}"):
            unique_name = f"{unique_name}"

        # --- Upload ---
        async with self._client() as client:
            await self._ensure_bucket(client)
            try:
                await client.put_object(
                    Bucket=cfg.s3_bucket_name,
                    Key=unique_name,
                    Body=content,
                    ContentType=detected_mime,
                )
            except ClientError as exc:
                code = exc.response["Error"]["Code"]
                logger.error("Upload failed for '%s' (code=%s): %s", file.filename, code, exc)
                if code in ("403", "AuthFailure"):
                    raise S3AuthError()
                raise BucketUnavailableError(cfg.s3_bucket_name)

        logger.info("Successfully uploaded '%s' as '%s'", file.filename, unique_name)
        return {
            "filename": unique_name,
            "original_filename": file.filename or "",
            "size_bytes": size,
            "mime_type": detected_mime,
        }

    async def get_presigned_url(self, filename: str) -> dict:
        """Generate a presigned GET URL for *filename*."""
        cfg = self._settings

        async with self._client() as client:
            await self._ensure_bucket(client)

            # Verify the object exists
            try:
                await client.head_object(Bucket=cfg.s3_bucket_name, Key=filename)
            except ClientError as exc:
                code = exc.response["Error"]["Code"]
                if code == "404":
                    logger.warning("File '%s' not found in bucket '%s'", filename, cfg.s3_bucket_name)
                    raise FileNotFoundInStorageError(filename)
                logger.error("head_object error for '%s': %s", filename, exc)
                raise BucketUnavailableError(cfg.s3_bucket_name)

            # Generate presigned URL
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": cfg.s3_bucket_name, "Key": filename},
                ExpiresIn=cfg.presigned_url_expiry,
            )

        logger.info("Generated presigned URL for '%s' (TTL=%ds)", filename, cfg.presigned_url_expiry)
        return {"filename": filename, "url": url, "expires_in_seconds": cfg.presigned_url_expiry}
