"""
Prometheus metrics registry.

Exported on GET /metrics (text/plain; version=0.0.4).

Metrics:
  http_requests_total{method, path, status}        — counter
  http_request_duration_seconds{method, path}      — histogram (p50/p90/p99)
  http_requests_in_flight{method, path}            — gauge
  app_errors_total{error_type, path}               — counter
  app_info{version, environment}                   — gauge (build metadata)
"""

from __future__ import annotations

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    REGISTRY,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from app.core.config import get_settings

_settings = get_settings()

# ── Metric definitions ─────────────────────────────────────────────────────

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

HTTP_REQUESTS_IN_FLIGHT = Gauge(
    "http_requests_in_flight",
    "Current number of HTTP requests being processed",
    ["method", "path"],
)

APP_ERRORS_TOTAL = Counter(
    "app_errors_total",
    "Total application errors by type",
    ["error_type", "path"],
)

APP_INFO = Info(
    "app",
    "Application metadata",
)


def init_metrics() -> None:
    """Register static application metadata."""
    APP_INFO.info({
        "version":     _settings.app_version,
        "environment": _settings.environment,
        "service":     _settings.otel_service_name,
    })


def metrics_output() -> tuple[bytes, str]:
    """Return (body_bytes, content_type) for the /metrics endpoint."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
