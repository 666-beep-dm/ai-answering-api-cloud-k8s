from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = Field("development", alias="APP_ENV")
    app_name: str = Field("RAG AI Service", alias="APP_NAME")
    app_version: str = Field("1.0.0", alias="APP_VERSION")
    debug: bool = Field(False, alias="DEBUG")
    secret_key: str = Field(..., alias="SECRET_KEY")

    # LLM
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o-mini", alias="OPENAI_MODEL")
    embedding_model: str = Field(
        "text-embedding-3-small", alias="EMBEDDING_MODEL"
    )

    # PostgreSQL
    db_url: str = Field(..., alias="DATABASE_URL")
    db_pool_size: int = Field(10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(20, alias="DB_MAX_OVERFLOW")

    # Redis
    redis_url: str = Field("redis://redis:6379/0", alias="REDIS_URL")
    cache_ttl_seconds: int = Field(3600, alias="CACHE_TTL_SECONDS")
    semantic_cache_threshold: float = Field(
        0.95, alias="SEMANTIC_CACHE_THRESHOLD"
    )

    # Observability
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    metrics_enabled: bool = Field(True, alias="METRICS_ENABLED")


@lru_cache
def get_settings() -> Settings:
    return Settings()
