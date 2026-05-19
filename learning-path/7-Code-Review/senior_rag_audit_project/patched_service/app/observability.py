"""patched_service/app/observability.py
Структурированное логирование (JSON) + OpenTelemetry трассирование.
"""

import logging
import json
import uuid
from contextvars import ContextVar
from typing import Any
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# ─── Trace-ID через ContextVar (thread/async safe) ───────────────────────────
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def generate_trace_id() -> str:
    return uuid.uuid4().hex


class JSONFormatter(logging.Formatter):
    """Структурированный JSON-лог без PII в payload."""

    def format(self, record: logging.LogRecord) -> str:
        log: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": trace_id_var.get(""),
        }
        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)
        return json.dumps(log, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.root.setLevel(level)
    logging.root.handlers = [handler]


def setup_tracing(endpoint: str, service_name: str) -> None:
    provider = TracerProvider()
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)
