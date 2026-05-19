"""Document repository — all DB access isolated here."""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.db.models import Document


class DocumentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, filename: str, s3_key: str, mime_type: str) -> Document:
        doc = Document(filename=filename, s3_key=s3_key, mime_type=mime_type)
        self._db.add(doc)
        await self._db.commit()
        await self._db.refresh(doc)
        return doc

    async def set_status(self, uid: str, status: str, chunks_count: int = 0) -> None:
        await self._db.execute(
            update(Document)
            .where(Document.uid == uid)
            .values(status=status, chunks_count=chunks_count)
        )
        await self._db.commit()

    async def get_by_uid(self, uid: str) -> Document | None:
        result = await self._db.execute(select(Document).where(Document.uid == uid))
        return result.scalar_one_or_none()
