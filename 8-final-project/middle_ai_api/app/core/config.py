"""Centralised configuration — single source of truth via .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    use_mock: bool = False  # set USE_MOCK=true to skip real API calls

    # S3-compatible storage
    s3_endpoint_url: str = ""          # leave empty for real AWS
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket_name: str = "ai-answering-api"
    s3_region: str = "us-east-1"

    # RAG
    vector_db_path: str = "./vector_db"
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k_chunks: int = 3
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Limits
    max_file_size_mb: int = 10

    # Logging
    log_level: str = "INFO"
    log_dir: str = "./logs"


settings = Settings()
