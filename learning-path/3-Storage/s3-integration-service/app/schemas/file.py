from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    filename: str = Field(..., description="Unique filename stored in S3")
    original_filename: str = Field(..., description="Original filename from the client")
    size_bytes: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="Detected MIME type")
    status: str = Field(default="uploaded", description="Upload status")

    model_config = {"json_schema_extra": {"example": {
        "filename": "3f2a1b_report.pdf",
        "original_filename": "report.pdf",
        "size_bytes": 204800,
        "mime_type": "application/pdf",
        "status": "uploaded",
    }}}


class PresignedUrlResponse(BaseModel):
    filename: str = Field(..., description="Filename in S3")
    url: str = Field(..., description="Presigned (or public) URL to access the file")
    expires_in_seconds: int = Field(..., description="URL TTL in seconds")

    model_config = {"json_schema_extra": {"example": {
        "filename": "3f2a1b_report.pdf",
        "url": "https://s3.example.com/bucket/3f2a1b_report.pdf?...",
        "expires_in_seconds": 3600,
    }}}
