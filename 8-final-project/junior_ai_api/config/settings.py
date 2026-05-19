"""Centralised configuration — reads from .env file."""

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

    # Set USE_MOCK=true to skip real API calls (no key required)
    use_mock: bool = False

    # Logging
    log_level: str = "INFO"


settings = Settings()
