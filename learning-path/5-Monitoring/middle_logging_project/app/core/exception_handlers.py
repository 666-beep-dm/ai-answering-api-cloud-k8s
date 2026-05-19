"""
Centralised exception handlers.
4xx (HTTPException, RequestValidationError) -> WARNING
5xx / unhandled                             -> ERROR + stack_trace
"""

import logging
import traceback

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.middlewares.request_context import request_id_ctx

logger = logging.getLogger("app.errors")


def _extra(request: Request, **kw) -> dict:
    return {
        "request_id": request_id_ctx.get("-"),
        "path":       request.url.path,
        "method":     request.method,
        **kw,
    }


async def _request_body_safe(request: Request) -> str:
    try:
        body = await request.body()
        return body.decode("utf-8", errors="replace")
    except Exception:
        return ""


# ── 422 Validation errors (Pydantic V2) ───────────────────────────────────
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning(
        "Validation error",
        extra=_extra(request, status_code=422, execution_time_ms=None),
    )
    # Pydantic V2 ctx may contain non-serialisable ValueError objects
    safe_errors = []
    for e in exc.errors():
        entry = dict(e)
        if "ctx" in entry:
            entry["ctx"] = {k: str(v) for k, v in entry["ctx"].items()}
        # url field is verbose and not needed in the response
        entry.pop("url", None)
        safe_errors.append(entry)
    return JSONResponse(
        status_code=422,
        content={"detail": safe_errors, "body": str(exc.body)},
    )


# ── 4xx HTTP errors ────────────────────────────────────────────────────────
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    level = logging.WARNING if exc.status_code < 500 else logging.ERROR
    logger.log(
        level,
        f"HTTP {exc.status_code}: {exc.detail}",
        extra=_extra(request, status_code=exc.status_code, execution_time_ms=None),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None) or {},
    )


# ── 5xx / unhandled exceptions ─────────────────────────────────────────────
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    body    = await _request_body_safe(request)
    headers = dict(request.headers)
    headers.pop("authorization", None)
    headers.pop("cookie", None)

    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {exc}",
        exc_info=(type(exc), exc, exc.__traceback__),
        extra=_extra(
            request,
            status_code=500,
            execution_time_ms=None,
            request_body=body[:2000],
            request_headers=headers,
        ),
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "error":  type(exc).__name__,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException,          http_exception_handler)
    app.add_exception_handler(Exception,              unhandled_exception_handler)
