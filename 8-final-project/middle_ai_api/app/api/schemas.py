"""Pydantic v2 request / response schemas."""

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class AnswerResponse(BaseModel):
    answer: str
    source_chunks_used: int = 0


class UploadResponse(BaseModel):
    filename: str
    s3_key: str
    chunks_indexed: int
    message: str


class HealthResponse(BaseModel):
    status: str
    s3_connected: bool
    vector_index_ready: bool
    indexed_chunks: int
