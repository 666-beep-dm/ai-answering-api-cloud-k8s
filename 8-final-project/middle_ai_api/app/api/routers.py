"""FastAPI routers: /upload, /ask, /health."""

import mimetypes
import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.schemas import AnswerResponse, HealthResponse, QuestionRequest, UploadResponse
from app.core.config import settings
from app.core.logging import get_logger
from app.services import llm_service, rag_service, s3_service

logger = get_logger(__name__)
router = APIRouter()

_ALLOWED_MIME = {"text/plain", "application/pdf"}
_MAX_BYTES = settings.max_file_size_mb * 1024 * 1024


# ── POST /upload ──────────────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(file: Annotated[UploadFile, File(description="A .txt or .pdf file (max 10 MB)")]) -> UploadResponse:
    # ── Validate size ─────────────────────────────────────────────────────────
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_file_size_mb} MB limit.",
        )

    # ── Validate MIME type ────────────────────────────────────────────────────
    mime = file.content_type or (mimetypes.guess_type(file.filename or "")[0] or "")
    if mime not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{mime}'. Allowed: {_ALLOWED_MIME}",
        )

    # ── Upload to S3 + index in RAG (parallel) ─────────────────────────────────
    filename = file.filename or f"upload_{uuid.uuid4().hex}"
    s3_key = f"uploads/{uuid.uuid4().hex}_{filename}"

    import asyncio
    s3_task = asyncio.create_task(s3_service.upload_file(s3_key, data, mime))
    rag_task = asyncio.create_task(rag_service.index_document(data, filename))

    s3_key_result, chunks_indexed = await asyncio.gather(s3_task, rag_task)
    logger.info(f"Upload complete: {filename} → {s3_key_result} | chunks: {chunks_indexed}")

    return UploadResponse(
        filename=filename,
        s3_key=s3_key_result,
        chunks_indexed=chunks_indexed,
        message="File uploaded and indexed successfully.",
    )


# ── POST /ask ─────────────────────────────────────────────────────────────────

@router.post("/ask", response_model=AnswerResponse)
async def ask(body: QuestionRequest) -> AnswerResponse:
    logger.info(f"Question received: {body.question[:80]}")

    # Retrieve relevant context
    chunks = await rag_service.retrieve(body.question)
    logger.info(f"Retrieved {len(chunks)} context chunks.")

    # Generate answer
    answer = await llm_service.ask_llm(body.question, chunks)

    return AnswerResponse(answer=answer, source_chunks_used=len(chunks))


# ── GET /health ───────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    import faiss as _faiss
    s3_ok = await s3_service.check_connection()
    idx_ready = rag_service.index_ready()
    indexed = rag_service._index.ntotal if rag_service._index is not None else 0

    overall = "ok" if s3_ok and idx_ready else "degraded"
    return HealthResponse(
        status=overall,
        s3_connected=s3_ok,
        vector_index_ready=idx_ready,
        indexed_chunks=indexed,
    )
