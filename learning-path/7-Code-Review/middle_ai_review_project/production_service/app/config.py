"""production_service/app/config.py
Централизованное, типизированное управление конфигурацией через pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_title: str = "AI Chat Service"
    app_version: str = "1.0.0"
    debug: bool = False

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 1024

    # Database
    database_url: str  # asyncpg DSN: postgresql+asyncpg://...

    # Security
    api_token_header: str = "X-API-Token"
    api_token_secret: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def masked_openai_key(self) -> str:
        """Возвращает маскированный ключ для безопасного логирования."""
        k = self.openai_api_key
        return f"{k[:6]}...{k[-4:]}" if len(k) > 10 else "***"


@lru_cache
def get_settings() -> Settings:
    return Settings()
