"""FastAPI router — thin HTTP adapter over FileService."""
from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import BaseConfig, get_settings
from app.db.session import get_db_session
from app.schemas.file import (
    FileListResponse, PresignedDownloadResponse,
    UploadInitResponse, UploadResponse,
)
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["Files"])


def get_service(
    cfg: BaseConfig = Depends(get_settings),
    session: AsyncSession = Depends(get_db_session),
) -> FileService:
    return FileService(cfg, session)


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=202,
    summary="Upload a file (server-side)",
    description=(
        "Upload via **multipart/form-data**. "
        "File is validated, pushed to S3, and metadata persisted asynchronously."
    ),
)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    svc: FileService = Depends(get_service),
) -> UploadResponse:
    result = await svc.upload_file(file, background_tasks)
    return UploadResponse(**result)


@router.post(
    "/upload/presigned",
    response_model=UploadInitResponse,
    status_code=201,
    summary="Initiate a presigned upload",
    description=(
        "Returns a **pre-signed PUT URL** so the client uploads directly to S3, "
        "bypassing the API server entirely."
    ),
)
async def init_presigned_upload(
    filename: str = Query(..., description="Original filename"),
    mime_type: str = Query("application/octet-stream", description="MIME type"),
    svc: FileService = Depends(get_service),
) -> UploadInitResponse:
    result = await svc.init_presigned_upload(filename, mime_type)
    return UploadInitResponse(**result)


@router.get(
    "/{file_id}/download",
    response_model=PresignedDownloadResponse,
    summary="Get a presigned download URL",
)
async def get_download_url(
    file_id: str,
    svc: FileService = Depends(get_service),
) -> PresignedDownloadResponse:
    result = await svc.get_download_url(file_id)
    return PresignedDownloadResponse(**result)


@router.get(
    "/",
    response_model=FileListResponse,
    summary="List uploaded files",
)
async def list_files(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: FileService = Depends(get_service),
) -> FileListResponse:
    result = await svc.list_files(limit, offset)
    return FileListResponse(**result)
