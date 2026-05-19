"""
app/core/models.py
Pydantic v2 request / response schemas.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2048, description="User query")
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievedChunk(BaseModel):
    text: str
    score: float


class RAGTimings(BaseModel):
    retrieval_time_ms: float
    reranking_time_ms: float
    llm_generation_time_ms: float
    total_time_ms: float


class AskResponse(BaseModel):
    query: str
    answer: str
    chunks: list[RetrievedChunk]
    timings: RAGTimings
    mode: str  # "buggy" | "optimized"
