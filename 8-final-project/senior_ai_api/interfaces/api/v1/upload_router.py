"""POST /api/v1/upload — accepts file, starts background indexing."""
import mimetypes, uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.logging import get_logger
from core.metrics import upload_errors_total
from domain.services.rag_service import ingest
from infrastructure.db.engine import get_db
from infrastructure.repositories.document_repo import DocumentRepository
from infrastructure.storage.s3_storage import upload as s3_upload
from interfaces.api.v1.schemas import UploadAccepted

router = APIRouter()
logger = get_logger(__name__)
_s = get_settings()

_ALLOWED = {"text/plain", "application/pdf"}
_MAX = _s.max_file_size_mb * 1024 * 1024


async def _background_index(uid: str, data: bytes, filename: str, db: AsyncSession) -> None:
    repo = DocumentRepository(db)
    try:
        count = await ingest(data, filename)
        await repo.set_status(uid, "indexed", count)
    except Exception as e:
        logger.error(f"Background indexing failed for {uid}: {e}")
        await repo.set_status(uid, "error")


@router.post("", response_model=UploadAccepted, status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    db: AsyncSession = Depends(get_db),
) -> UploadAccepted:
    data = await file.read()

    if len(data) > _MAX:
        upload_errors_total.inc()
        raise HTTPException(413, detail=f"File exceeds {_s.max_file_size_mb} MB.")

    mime = file.content_type or (mimetypes.guess_type(file.filename or "")[0] or "")
    if mime not in _ALLOWED:
        upload_errors_total.inc()
        raise HTTPException(415, detail=f"Unsupported MIME type: {mime}")

    filename = file.filename or f"upload_{uuid.uuid4().hex}"
    s3_key = f"uploads/{uuid.uuid4().hex}_{filename}"

    await s3_upload(s3_key, data, mime)

    repo = DocumentRepository(db)
    doc = await repo.create(filename=filename, s3_key=s3_key, mime_type=mime)

    # Heavy indexing runs in background — user gets 202 immediately
    background_tasks.add_task(_background_index, doc.uid, data, filename, db)

    return UploadAccepted(
        document_uid=doc.uid,
        filename=filename,
        message="File accepted. Indexing started in background.",
    )
