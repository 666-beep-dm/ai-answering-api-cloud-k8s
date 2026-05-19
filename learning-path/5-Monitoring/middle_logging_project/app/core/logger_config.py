"""
Structured JSON logging configuration.

Every log record is emitted as a single-line JSON object with the fields:
    timestamp, level, message, logger, request_id,
    path, method, status_code, execution_time_ms,
    stack_trace (only on errors)
"""

import logging
import os
import json
import traceback
from datetime import datetime, timezone

# ── Settings from env ─────────────────────────────────────────────────────
LOG_LEVEL   = os.getenv("LOG_LEVEL",   "INFO").upper()
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "false").lower() == "true"
LOG_FILE    = os.getenv("LOG_FILE",    "logs/app.log")


class JsonFormatter(logging.Formatter):
    """
    Formats every LogRecord as a single-line JSON string.
    New-lines inside messages / stack traces are escaped to \\n
    so the output stays a valid NDJSON stream.
    """

    # Fields that we pull directly from the LogRecord and want in the output.
    RECORD_ATTRS = {
        "request_id", "path", "method",
        "status_code", "execution_time_ms",
    }

    def format(self, record: logging.LogRecord) -> str:
        # Base fields always present
        payload: dict = {
            "timestamp":  datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level":      record.levelname,
            "logger":     record.name,
            "message":    record.getMessage(),
        }

        # Optional request-context fields (injected by middleware)
        for attr in self.RECORD_ATTRS:
            value = getattr(record, attr, None)
            if value is not None:
                payload[attr] = value

        # Stack trace — collapse to a single escaped string
        if record.exc_info:
            payload["stack_trace"] = "".join(
                traceback.format_exception(*record.exc_info)
            ).replace("\n", "\\n").strip()

        # Ensure no raw newlines leak into the JSON value strings
        for key, val in payload.items():
            if isinstance(val, str):
                payload[key] = val.replace("\n", "\\n")

        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> logging.Logger:
    """Configure root logger and return the application logger."""
    level = getattr(logging, LOG_LEVEL, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers to avoid duplicate output
    root.handlers.clear()

    formatter = JsonFormatter()

    # ── Console handler ───────────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # ── File handler (optional) ───────────────────────────────────────────
    if LOG_TO_FILE:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    logger = logging.getLogger("app")
    logger.info(
        "Logging initialised",
        extra={"request_id": "startup", "path": "-", "method": "-"},
    )
    return logger


# Module-level singleton — import this everywhere
logger = setup_logging()
