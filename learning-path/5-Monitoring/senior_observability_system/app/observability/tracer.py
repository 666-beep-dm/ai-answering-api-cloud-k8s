"""
OpenTelemetry Distributed Tracing.

Exporter strategy (OTEL_EXPORTER env var):
  • console  — prints structured JSON spans to stdout (default / dev)
  • otlp     — sends to gRPC collector at OTEL_OTLP_ENDPOINT
                (requires opentelemetry-exporter-otlp-proto-grpc)

Span context is propagated via W3C TraceContext headers
(traceparent / tracestate) — compatible with Jaeger, Tempo, Zipkin.

To wire full auto-instrumentation add to main.py startup:
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.trace import Span, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from app.core.config import get_settings

_settings  = get_settings()
_log       = logging.getLogger("app.tracer")
_propagator = TraceContextTextMapPropagator()

_provider: TracerProvider | None = None
_tracer:   trace.Tracer  | None = None


def init_tracer() -> trace.Tracer:
    """Initialise and return the global tracer. Idempotent."""
    global _provider, _tracer
    if _tracer is not None:
        return _tracer

    resource = Resource.create({
        SERVICE_NAME:    _settings.otel_service_name,
        SERVICE_VERSION: _settings.app_version,
        "deployment.environment": _settings.environment,
    })
    _provider = TracerProvider(resource=resource)

    if _settings.otel_exporter == "otlp":
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            exporter = OTLPSpanExporter(endpoint=_settings.otel_otlp_endpoint)
            _provider.add_span_processor(BatchSpanProcessor(exporter))
            _log.info("OTel: OTLP exporter → %s", _settings.otel_otlp_endpoint)
        except ImportError:
            _log.warning(
                "OTel: opentelemetry-exporter-otlp-proto-grpc not installed; "
                "falling back to console exporter."
            )
            _provider.add_span_processor(
                SimpleSpanProcessor(ConsoleSpanExporter())
            )
    else:
        _provider.add_span_processor(
            SimpleSpanProcessor(ConsoleSpanExporter())
        )
        _log.info("OTel: Console exporter active (dev mode)")

    trace.set_tracer_provider(_provider)
    _tracer = trace.get_tracer(_settings.otel_service_name)
    _log.info("OTel tracer initialised: service=%s", _settings.otel_service_name)
    return _tracer


def get_tracer() -> trace.Tracer:
    if _tracer is None:
        return init_tracer()
    return _tracer


def extract_context(headers: dict) -> object:
    """Extract W3C trace context from inbound request headers."""
    return _propagator.extract(carrier=headers)


def inject_context(headers: dict) -> None:
    """Inject W3C trace context into outbound request headers."""
    _propagator.inject(carrier=headers)


@contextmanager
def start_span(
    name: str,
    attributes: dict | None = None,
) -> Generator[Span, None, None]:
    """Context manager — creates a child span, records exceptions automatically."""
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, str(v))
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


def current_trace_id() -> str:
    ctx = trace.get_current_span().get_span_context()
    if ctx and ctx.is_valid:
        return format(ctx.trace_id, "032x")
    return "0" * 32


def current_span_id() -> str:
    ctx = trace.get_current_span().get_span_context()
    if ctx and ctx.is_valid:
        return format(ctx.span_id, "016x")
    return "0" * 16
