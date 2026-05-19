"""
Centralised application configuration via pydantic-settings v2.
All values are overridable through environment variables or a .env file.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────────────
    app_name: str = Field("SeniorObservabilityService", alias="APP_NAME")
    app_version: str = Field("1.0.0", alias="APP_VERSION")
    environment: Literal["development", "staging", "production"] = Field(
        "development", alias="ENVIRONMENT"
    )
    debug: bool = Field(False, alias="DEBUG")

    # ── Server ────────────────────────────────────────────────────────────
    host: str = Field("0.0.0.0", alias="HOST")
    port: int = Field(8000, alias="PORT")
    workers: int = Field(1, alias="WORKERS")

    # ── Logging ───────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", alias="LOG_LEVEL"
    )
    log_to_file: bool = Field(False, alias="LOG_TO_FILE")
    log_file: str = Field("logs/app.log", alias="LOG_FILE")

    # ── Tracing ───────────────────────────────────────────────────────────
    otel_enabled: bool = Field(True, alias="OTEL_ENABLED")
    otel_service_name: str = Field("fastapi-observability", alias="OTEL_SERVICE_NAME")
    otel_exporter: Literal["console", "otlp"] = Field("console", alias="OTEL_EXPORTER")
    otel_otlp_endpoint: str = Field(
        "http://localhost:4317", alias="OTEL_OTLP_ENDPOINT"
    )

    # ── Metrics ───────────────────────────────────────────────────────────
    metrics_enabled: bool = Field(True, alias="METRICS_ENABLED")
    metrics_path: str = Field("/metrics", alias="METRICS_PATH")

    # ── Alerting thresholds ───────────────────────────────────────────────
    alert_error_rate_threshold: float = Field(0.05, alias="ALERT_ERROR_RATE_THRESHOLD")
    alert_latency_threshold_ms: float = Field(500.0, alias="ALERT_LATENCY_THRESHOLD_MS")
    alert_window_seconds: int = Field(60, alias="ALERT_WINDOW_SECONDS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
