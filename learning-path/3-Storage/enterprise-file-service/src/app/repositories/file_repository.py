"""Repository layer — isolates all DB queries from business logic."""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_record import FileRecord


class FileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(
        self, *, original_filename: str, s3_key: str,
        mime_type: str, size_bytes: int, status: str = "pending",
    ) -> FileRecord:
        record = FileRecord(
            id=str(uuid.uuid4()),
            original_filename=original_filename,
            s3_key=s3_key,
            mime_type=mime_type,
            size_bytes=size_bytes,
            status=status,
        )
        self._s.add(record)
        await self._s.flush()
        await self._s.refresh(record)
        return record

    async def get_by_id(self, file_id: str) -> FileRecord | None:
        result = await self._s.execute(
            select(FileRecord).where(FileRecord.id == file_id)
        )
        return result.scalar_one_or_none()

    async def update_status(self, file_id: str, status: str) -> None:
        await self._s.execute(
            update(FileRecord)
            .where(FileRecord.id == file_id)
            .values(status=status, updated_at=datetime.utcnow())
        )

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[FileRecord]:
        result = await self._s.execute(
            select(FileRecord).order_by(FileRecord.created_at.desc())
            .limit(limit).offset(offset)
        )
        return list(result.scalars().all())
