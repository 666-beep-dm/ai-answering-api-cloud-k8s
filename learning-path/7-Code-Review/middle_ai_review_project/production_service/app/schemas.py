"""production_service/app/schemas.py — Pydantic v2 Request/Response схемы."""

from pydantic import BaseModel, Field, field_validator


# ─── Chat ─────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_id: int = Field(..., gt=0, description="ID пользователя")
    message: str = Field(..., min_length=1, max_length=4096, description="Сообщение")

    @field_validator("message")
    @classmethod
    def strip_message(cls, v: str) -> str:
        return v.strip()


class ChatResponse(BaseModel):
    response: str
    tokens_used: int


# ─── History ──────────────────────────────────────────────────────────────────

class HistoryItem(BaseModel):
    message: str
    response: str


class HistoryResponse(BaseModel):
    user_id: int
    items: list[HistoryItem]


# ─── Summarize ────────────────────────────────────────────────────────────────

class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=16_384)


class SummarizeResponse(BaseModel):
    summary: str
    tokens_used: int


# ─── Models ───────────────────────────────────────────────────────────────────

class ModelListResponse(BaseModel):
    models: list[str]
