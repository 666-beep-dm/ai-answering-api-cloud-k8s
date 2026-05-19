"""
app/core/config.py
Centralized settings — Pydantic v2 + pydantic-settings.
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────
    APP_ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    WORKERS: int = Field(default=2)

    # ── Vector DB (FAISS-based mock) ──────────────────────────────────
    VECTOR_DIM: int = Field(default=384)
    VECTOR_CORPUS_SIZE: int = Field(default=5000)
    TOP_K: int = Field(default=5)

    # ── LLM (mocked external API) ────────────────────────────────────
    LLM_API_URL: str = Field(default="http://mock-llm:8080/generate")
    LLM_TIMEOUT_BUG: float = Field(default=0.0)   # 0 = no timeout (BUG)
    LLM_TIMEOUT_FIX: float = Field(default=30.0)  # explicit timeout (FIX)

    # ── Bottleneck simulation knobs ───────────────────────────────────
    SIMULATE_BLOCKING_IO_SECONDS: float = Field(default=3.0)
    SIMULATE_LLM_DELAY_SECONDS: float = Field(default=6.0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
