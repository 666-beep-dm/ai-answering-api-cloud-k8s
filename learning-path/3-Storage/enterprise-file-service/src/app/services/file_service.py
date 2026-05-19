"""
Business-logic layer.
Coordinates storage ↔ repository, triggers background tasks.
"""
from __future__ import annotations
from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import BaseConfig
from app.core.exceptions import FileRecordNotFoundError
from app.core.logging import get_logger
from app.repositories.file_repository import FileRepository
from app.storage.s3_storage import S3Storage

log = get_logger(__name__)


class FileService:
    def __init__(self, cfg: BaseConfig, session: AsyncSession) -> None:
        self._cfg = cfg
        self._repo = FileRepository(session)
        self._storage = S3Storage(cfg)

    # ── Direct upload flow ────────────────────────────────────────────────────

    async def upload_file(
        self, file: UploadFile, background_tasks: BackgroundTasks
    ) -> dict:
        content = await file.read()
        meta = await self._storage.upload_bytes(content, file.filename or "unknown")

        # Persist metadata with "processing" status; finalize in background
        record = await self._repo.create(
            original_filename=file.filename or "unknown",
            s3_key=meta["s3_key"],
            mime_type=meta["mime_type"],
            size_bytes=meta["size_bytes"],
            status="processing",
        )

        background_tasks.add_task(self._finalize_record, record.id)

        log.info("File '%s' queued (id=%s)", file.filename, record.id)
        return {
            "file_id": record.id,
            "filename": meta["s3_key"],
            "original_filename": record.original_filename,
            "size_bytes": meta["size_bytes"],
            "mime_type": meta["mime_type"],
            "status": "processing",
        }

    async def _finalize_record(self, file_id: str) -> None:
        """Background task: mark record as uploaded after post-processing."""
        import asyncio
        from app.db.session import AsyncSessionFactory
        await asyncio.sleep(0.1)  # simulate lightweight post-processing
        async with AsyncSessionFactory() as session:
            repo = FileRepository(session)
            await repo.update_status(file_id, "uploaded")
            await session.commit()
        log.info("Record %s finalized → uploaded", file_id)

    # ── Presigned-upload flow ─────────────────────────────────────────────────

    async def init_presigned_upload(self, filename: str, mime_type: str) -> dict:
        """Pre-create DB record; return presigned PUT URL for direct S3 upload."""
        import uuid
        s3_key = f"{uuid.uuid4().hex}_{filename}"
        record = await self._repo.create(
            original_filename=filename, s3_key=s3_key,
            mime_type=mime_type, size_bytes=0, status="pending_upload",
        )
        url = await self._storage.generate_presigned_upload_url(s3_key)
        return {
            "file_id": record.id,
            "presigned_url": url,
            "expires_in_seconds": self._cfg.presigned_upload_ttl,
        }

    # ── Download ──────────────────────────────────────────────────────────────

    async def get_download_url(self, file_id: str) -> dict:
        record = await self._repo.get_by_id(file_id)
        if not record:
            raise FileRecordNotFoundError(file_id)
        url = await self._storage.generate_presigned_download_url(record.s3_key)
        return {
            "file_id": file_id,
            "filename": record.s3_key,
            "url": url,
            "expires_in_seconds": self._cfg.presigned_download_ttl,
        }

    # ── Listing ───────────────────────────────────────────────────────────────

    async def list_files(self, limit: int = 100, offset: int = 0) -> dict:
        records = await self._repo.list_all(limit, offset)
        return {"items": records, "total": len(records)}
