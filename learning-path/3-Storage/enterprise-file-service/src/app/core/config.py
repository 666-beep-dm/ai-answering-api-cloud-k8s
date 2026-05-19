"""
12-Factor App configuration via pydantic-settings.
Reads from environment / .env file.  Splits into Base → Dev → Prod profiles.
"""
from __future__ import annotations
from functools import lru_cache
from typing import Literal
from pydantic import AnyUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """Shared settings present in every environment."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    environment: Literal["development", "production", "test"] = "development"
    app_name: str = "Enterprise File Service"
    app_version: str = "1.0.0"
    debug: bool = False

    # ── Database ─────────────────────────────────────────────────────────────
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "fileservice"
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def sync_database_url(self) -> str:
        """Used by Alembic (sync driver)."""
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # ── Redis ────────────────────────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    cache_ttl_seconds: int = 3600

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ── S3 / Object Storage ──────────────────────────────────────────────────
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_bucket_name: str = "enterprise-files"
    s3_region: str = "us-east-1"
    presigned_upload_ttl: int = 900    # 15 min
    presigned_download_ttl: int = 3600 # 1 h

    # ── Upload constraints ───────────────────────────────────────────────────
    max_file_size_mb: int = 100
    allowed_mime_types: list[str] = [
        "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml",
        "application/pdf",
        "text/plain", "text/csv", "text/html",
        "application/json",
        "application/zip", "application/x-tar",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]

    # ── Resilience ───────────────────────────────────────────────────────────
    s3_retry_attempts: int = 3
    s3_retry_wait_seconds: float = 1.0


class DevConfig(BaseConfig):
    environment: Literal["development", "production", "test"] = "development"
    debug: bool = True


class ProdConfig(BaseConfig):
    environment: Literal["development", "production", "test"] = "production"
    debug: bool = False
    db_pool_size: int = 20
    db_max_overflow: int = 40


@lru_cache
def get_settings() -> BaseConfig:
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        return ProdConfig()
    return DevConfig()


import os  # noqa: E402 (needed for get_settings)
