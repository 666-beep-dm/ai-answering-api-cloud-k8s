"""
Structured JSON logger.

Field schema is designed for Loki label-indexing:
  • Static (low-cardinality) labels: service, environment, level
  • Dynamic fields: timestamp, message, trace_id, span_id, request_id,
                     path, method, status_code, execution_time_ms,
                     stack_trace (errors only)

Vector / Fluentbit pipeline snippet (docker labels):
    [FILTER]
        Name   parser
        Match  docker.*
        Parser json
    → Loki labels: {service, environment, level}
"""

from __future__ import annotations

import json
import logging
import os
import traceback
from datetime import datetime, timezone

from app.core.config import get_settings

_settings = get_settings()


class _LokiReadyFormatter(logging.Formatter):
    """Single-line JSON formatter; all newlines escaped inside values."""

    _STATIC_LABELS = {
        "service":     _settings.otel_service_name,
        "environment": _settings.environment,
        "version":     _settings.app_version,
    }

    _EXTRA_FIELDS = frozenset({
        "trace_id", "span_id", "request_id",
        "path", "method", "status_code", "execution_time_ms",
        "request_body", "request_headers",
    })

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level":   record.levelname,
            "logger":  record.name,
            "message": record.getMessage(),
            **self._STATIC_LABELS,
        }

        for field in self._EXTRA_FIELDS:
            v = getattr(record, field, None)
            if v is not None:
                payload[field] = v

        if record.exc_info:
            payload["stack_trace"] = "".join(
                traceback.format_exception(*record.exc_info)
            ).replace("\n", "\\n").strip()

        # Escape stray newlines in all string values
        for k, v in payload.items():
            if isinstance(v, str):
                payload[k] = v.replace("\n", "\\n")

        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> logging.Logger:
    level = getattr(logging, _settings.log_level, logging.INFO)
    root  = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    fmt = _LokiReadyFormatter()

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    if _settings.log_to_file:
        os.makedirs(os.path.dirname(_settings.log_file), exist_ok=True)
        fh = logging.FileHandler(_settings.log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)

    log = logging.getLogger("app")
    log.info("Logging initialised", extra={
        "trace_id": "startup", "span_id": "0",
        "request_id": "startup", "path": "-", "method": "-",
    })
    return log


logger = setup_logging()
