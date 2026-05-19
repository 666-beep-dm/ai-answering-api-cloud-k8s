from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    session_id: str = Field(default="default", max_length=128)
    stream: bool = Field(True, description="Enable SSE streaming")
    top_k: int = Field(4, ge=1, le=10, description="Number of context chunks")


class SourceDocument(BaseModel):
    content: str
    metadata: dict = {}
    score: float = 0.0


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceDocument] = []
    was_cached: bool = False
    latency_ms: float


class ConversationRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    question: str
    answer: str | None
    num_sources: int
    latency_ms: float | None
    was_cached: bool
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    version: str
    env: str
