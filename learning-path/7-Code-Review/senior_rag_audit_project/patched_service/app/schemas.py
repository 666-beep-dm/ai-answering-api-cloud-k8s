"""patched_service/app/schemas.py — Pydantic v2 схемы."""

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8192)


class QueryResponse(BaseModel):
    response: str
    cached: bool
    tokens_used: int
    cost_usd: float


class DocumentItem(BaseModel):
    content: str = Field(..., min_length=1, max_length=65536)
    source: str | None = None


class IngestRequest(BaseModel):
    documents: list[DocumentItem] = Field(..., min_length=1, max_length=100)


class HealthResponse(BaseModel):
    status: str
    service: str
