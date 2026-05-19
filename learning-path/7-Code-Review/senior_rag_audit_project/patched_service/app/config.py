"""patched_service/app/config.py — централизованная конфигурация."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 2048
    openai_max_retries: int = 3
    openai_timeout: float = 30.0

    # Database
    database_url: str

    # Redis
    redis_url: str

    # Semantic cache
    semantic_cache_threshold: float = Field(default=0.92, ge=0.0, le=1.0)
    cache_ttl_seconds: int = 3600

    # Celery
    celery_concurrency: int = 4

    # Observability
    otel_service_name: str = "rag-api"
    otel_exporter_endpoint: str = "http://otel-collector:4317"
    log_level: str = "INFO"

    # Security
    api_token_secret: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def masked_key(self) -> str:
        k = self.openai_api_key
        return f"{k[:6]}...{k[-4:]}" if len(k) > 10 else "***"


@lru_cache
def get_settings() -> Settings:
    return Settings()
