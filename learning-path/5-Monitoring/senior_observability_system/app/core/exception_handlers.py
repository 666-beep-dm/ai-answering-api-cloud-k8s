"""
Centralised exception handlers with observability context.
4xx → WARNING,  5xx → ERROR + stack_trace
"""
from __future__ import annotations

import logging
import traceback

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.observability.middleware import request_id_ctx, trace_id_ctx, span_id_ctx
from app.observability.metrics import APP_ERRORS_TOTAL

_log = logging.getLogger("app.errors")


def _ctx(request: Request, **kw) -> dict:
    return {
        "trace_id":   trace_id_ctx.get("0" * 32),
        "span_id":    span_id_ctx.get("0" * 16),
        "request_id": request_id_ctx.get("-"),
        "path":       request.url.path,
        "method":     request.method,
        **kw,
    }


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    _log.warning("Validation error", extra=_ctx(request, status_code=422))
    safe = []
    for e in exc.errors():
        entry = dict(e)
        if "ctx" in entry:
            entry["ctx"] = {k: str(v) for k, v in entry["ctx"].items()}
        entry.pop("url", None)
        safe.append(entry)
    return JSONResponse(status_code=422,
                        content={"detail": safe, "body": str(exc.body)})


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    level = logging.WARNING if exc.status_code < 500 else logging.ERROR
    _log.log(level, "HTTP %s: %s", exc.status_code, exc.detail,
             extra=_ctx(request, status_code=exc.status_code))
    if exc.status_code >= 500:
        APP_ERRORS_TOTAL.labels(
            error_type="HTTPException", path=request.url.path
        ).inc()
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None) or {},
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    try:
        body = (await request.body()).decode("utf-8", errors="replace")
    except Exception:
        body = ""
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in {"authorization", "cookie"}}

    _log.error(
        "Unhandled exception: %s: %s", type(exc).__name__, exc,
        exc_info=(type(exc), exc, exc.__traceback__),
        extra=_ctx(request, status_code=500,
                   request_body=body[:2000],
                   request_headers=headers),
    )
    APP_ERRORS_TOTAL.labels(
        error_type=type(exc).__name__, path=request.url.path
    ).inc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": type(exc).__name__},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException,          http_exception_handler)
    app.add_exception_handler(Exception,              unhandled_exception_handler)
