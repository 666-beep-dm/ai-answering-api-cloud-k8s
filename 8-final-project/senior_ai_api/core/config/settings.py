"""Pydantic-settings config — reads from .env (dev or prod)."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    # App
    app_env: str = "development"
    debug: bool = False
    secret_key: str = "changeme"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    use_mock: bool = False

    # PostgreSQL (asyncpg)
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "ai_api"
    postgres_user: str = "ai_user"
    postgres_password: str = "changeme"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_url: str = "redis://redis:6379/0"
    cache_ttl_seconds: int = 300

    # S3
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket_name: str = "ai-answering-api"
    s3_region: str = "us-east-1"

    # Vector DB (Qdrant)
    qdrant_host: str = "vector-db"
    qdrant_port: int = 6333
    qdrant_collection: str = "documents"

    # RAG
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k_chunks: int = 3
    max_file_size_mb: int = 10

    # Observability
    log_level: str = "INFO"
    prometheus_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
