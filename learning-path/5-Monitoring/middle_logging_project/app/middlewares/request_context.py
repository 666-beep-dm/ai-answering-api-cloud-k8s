"""
Pure ASGI request-context middleware.

Wraps the entire ASGI app (including FastAPI exception handlers) so that
ZeroDivisionError / RuntimeError are converted to JSON 500 responses by
the app-level handlers BEFORE we try to log the status code.

Starlette >= 0.35 BaseHTTPMiddleware.call_next re-raises app exceptions
past the exception-handler layer, making it impossible to log the HTTP
status from a class-based middleware.  A pure ASGI wrapper sits outside
the entire stack and sees only final responses — never raw exceptions.
"""

import json
import logging
import time
import traceback
import uuid
from contextvars import ContextVar
from typing import Callable

from starlette.types import ASGIApp, Receive, Scope, Send

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
logger = logging.getLogger("app.middleware")


def _extra(rid: str, path: str, method: str, **kw) -> dict:
    return {"request_id": rid, "path": path, "method": method, **kw}


class RequestContextMiddleware:
    """Pure ASGI middleware — no BaseHTTPMiddleware dependency."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        rid    = str(uuid.uuid4())
        token  = request_id_ctx.set(rid)
        path   = scope.get("path", "")
        method = scope.get("method", "")
        start  = time.perf_counter()

        logger.info(f"→ {method} {path}", extra=_extra(rid, path, method))

        # Intercept the first send call to capture the status code
        status_code = 500
        response_started = False

        async def send_wrapper(message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_started = True
                # Inject X-Request-ID into response headers
                headers = list(message.get("headers", []))
                headers.append(
                    (b"x-request-id", rid.encode())
                )
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            # Should not normally reach here because FastAPI exception
            # handlers convert everything to responses, but just in case.
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error(
                f"Unhandled ASGI exception: {type(exc).__name__}: {exc}",
                exc_info=True,
                extra=_extra(rid, path, method,
                             status_code=500, execution_time_ms=elapsed_ms),
            )
            if not response_started:
                body = json.dumps({"detail": "Internal Server Error",
                                   "error": type(exc).__name__}).encode()
                await send({"type": "http.response.start",
                            "status": 500,
                            "headers": [[b"content-type", b"application/json"],
                                        [b"content-length", str(len(body)).encode()]]})
                await send({"type": "http.response.body", "body": body})
            return
        finally:
            request_id_ctx.reset(token)

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            f"← {method} {path} {status_code}",
            extra=_extra(rid, path, method,
                         status_code=status_code,
                         execution_time_ms=elapsed_ms),
        )
