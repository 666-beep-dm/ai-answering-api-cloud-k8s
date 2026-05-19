"""
Unified Observability Middleware (pure ASGI).

Per-request pipeline:
  1. Extract / generate X-Trace-ID and X-Request-ID
  2. Open an OpenTelemetry span (W3C TraceContext propagation)
  3. Start Prometheus in-flight gauge
  4. Call downstream app
  5. Record Prometheus counter + histogram
  6. Feed alerting sliding-window
  7. Inject X-Trace-ID + X-Request-ID into response headers
  8. Close OTel span

Uses pure ASGI (__call__) to guarantee that FastAPI exception handlers
fire BEFORE the middleware logs the final status code.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar

from opentelemetry import trace
from opentelemetry.trace import SpanKind
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import get_settings
from app.observability.metrics import (
    APP_ERRORS_TOTAL,
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS_IN_FLIGHT,
    HTTP_REQUESTS_TOTAL,
)
from app.observability.tracer import (
    current_span_id,
    current_trace_id,
    extract_context,
    get_tracer,
)
from app.observability.alerting import alerting_engine

_settings = get_settings()
_log      = logging.getLogger("app.middleware")

trace_id_ctx:   ContextVar[str] = ContextVar("trace_id",   default="0" * 32)
span_id_ctx:    ContextVar[str] = ContextVar("span_id",    default="0" * 16)
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

_SKIP_PATHS = frozenset({_settings.metrics_path, "/docs", "/redoc",
                          "/openapi.json", "/health"})


class ObservabilityMiddleware:
    """Pure ASGI observability middleware."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path   = scope.get("path", "/")
        method = scope.get("method", "GET")

        # Skip observability overhead for internal paths
        if path in _SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        # ── 1. IDs ────────────────────────────────────────────────────────
        raw_headers = dict(scope.get("headers", []))
        incoming    = {
            k.decode(): v.decode()
            for k, v in raw_headers.items()
        }

        rid   = incoming.get("x-request-id") or str(uuid.uuid4())
        t_rid = incoming.get("x-trace-id")   or str(uuid.uuid4())

        tok_r = request_id_ctx.set(rid)
        tok_t = trace_id_ctx.set(t_rid)

        # ── 2. OTel span ──────────────────────────────────────────────────
        ctx     = extract_context(incoming)
        tracer  = get_tracer()
        span_name = f"{method} {path}"

        with tracer.start_as_current_span(
            span_name,
            context=ctx,
            kind=SpanKind.SERVER,
            attributes={
                "http.method":  method,
                "http.url":     path,
                "http.host":    incoming.get("host", ""),
                "request_id":   rid,
                "x_trace_id":   t_rid,
            },
        ) as span:
            otel_trace = current_trace_id()
            otel_span  = current_span_id()
            tok_s = span_id_ctx.set(otel_span)

            _extra = {
                "trace_id":   otel_trace,
                "span_id":    otel_span,
                "request_id": rid,
                "path":       path,
                "method":     method,
            }
            _log.info("→ %s %s", method, path, extra=_extra)

            # ── 3. In-flight gauge ─────────────────────────────────────────
            HTTP_REQUESTS_IN_FLIGHT.labels(method=method, path=path).inc()
            start = time.perf_counter()
            status_code = 500
            response_started = False

            # ── 4+7. Send wrapper: capture status + inject headers ─────────
            async def send_wrapper(message) -> None:
                nonlocal status_code, response_started
                if message["type"] == "http.response.start":
                    status_code = message["status"]
                    response_started = True
                    headers = list(message.get("headers", []))
                    headers += [
                        (b"x-request-id", rid.encode()),
                        (b"x-trace-id",   t_rid.encode()),
                        (b"x-span-id",    otel_span.encode()),
                    ]
                    message = {**message, "headers": headers}
                await send(message)

            try:
                await self.app(scope, receive, send_wrapper)
            except Exception as exc:
                # The inner app (exception handler layer) already sent a
                # 500 response via send_wrapper — we must NOT re-raise or
                # the test client / ServerErrorMiddleware will swallow the
                # response and surface the raw exception instead.
                APP_ERRORS_TOTAL.labels(
                    error_type=type(exc).__name__, path=path
                ).inc()
                span.record_exception(exc)
                if not response_started:
                    # No response was sent yet — let it bubble
                    raise
                # Response already committed — log and absorb
                import logging as _logging
                _logging.getLogger("app.middleware").debug(
                    "Exception absorbed after response committed: %s", exc
                )
            finally:
                elapsed     = time.perf_counter() - start
                elapsed_ms  = round(elapsed * 1000, 2)

                # ── 5. Prometheus ──────────────────────────────────────────
                HTTP_REQUESTS_TOTAL.labels(
                    method=method, path=path, status=str(status_code)
                ).inc()
                HTTP_REQUEST_DURATION.labels(
                    method=method, path=path
                ).observe(elapsed)
                HTTP_REQUESTS_IN_FLIGHT.labels(method=method, path=path).dec()

                span.set_attribute("http.status_code", status_code)

                _log.info(
                    "← %s %s %s  %.2f ms",
                    method, path, status_code, elapsed_ms,
                    extra={**_extra,
                           "status_code": status_code,
                           "execution_time_ms": elapsed_ms},
                )

                # ── 6. Alerting ────────────────────────────────────────────
                import asyncio
                asyncio.ensure_future(
                    alerting_engine.record(status_code, elapsed_ms, path, method)
                )

                span_id_ctx.reset(tok_s)
                request_id_ctx.reset(tok_r)
                trace_id_ctx.reset(tok_t)
