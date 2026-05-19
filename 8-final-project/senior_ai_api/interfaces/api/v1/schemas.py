"""Pydantic v2 API schemas."""
from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class UploadAccepted(BaseModel):
    document_uid: str
    filename: str
    message: str


class HealthResponse(BaseModel):
    status: str
    postgres: bool
    redis: bool
    s3: bool
    vector_db: bool
