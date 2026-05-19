from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class FileRecordOut(BaseModel):
    id: str
    original_filename: str
    s3_key: str
    mime_type: str
    size_bytes: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UploadInitResponse(BaseModel):
    """Response for presigned-upload flow: client PUTs directly to S3."""
    file_id: str = Field(..., description="Pre-created DB record ID")
    presigned_url: str = Field(..., description="S3 presigned PUT URL")
    expires_in_seconds: int


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    original_filename: str
    size_bytes: int
    mime_type: str
    status: str = "uploaded"


class PresignedDownloadResponse(BaseModel):
    file_id: str
    filename: str
    url: str
    expires_in_seconds: int


class FileListResponse(BaseModel):
    items: list[FileRecordOut]
    total: int
