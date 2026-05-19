from fastapi import APIRouter, Depends, File, UploadFile

from app.core.config import Settings, get_settings
from app.schemas.file import PresignedUrlResponse, UploadResponse
from app.services.s3_service import S3Service

router = APIRouter(prefix="/files", tags=["S3 Storage"])


def get_s3_service(settings: Settings = Depends(get_settings)) -> S3Service:
    return S3Service(settings)


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=201,
    summary="Upload a file to S3",
    description=(
        "Accepts a file via **multipart/form-data**.\n\n"
        "- Maximum size: configurable via `MAX_FILE_SIZE_MB` (default 10 MB).\n"
        "- Allowed MIME types: jpeg, png, gif, webp, pdf, txt, csv, zip, json.\n"
        "- Returns the unique S3 key and metadata."
    ),
)
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    s3: S3Service = Depends(get_s3_service),
) -> UploadResponse:
    result = await s3.upload_file(file)
    return UploadResponse(**result)


@router.get(
    "/{filename}",
    response_model=PresignedUrlResponse,
    summary="Get a presigned URL for a file",
    description=(
        "Returns a time-limited presigned URL that grants read access to the file.\n\n"
        "The TTL is configurable via `PRESIGNED_URL_EXPIRY` (default 3600 seconds)."
    ),
)
async def get_file_url(
    filename: str,
    s3: S3Service = Depends(get_s3_service),
) -> PresignedUrlResponse:
    result = await s3.get_presigned_url(filename)
    return PresignedUrlResponse(**result)
