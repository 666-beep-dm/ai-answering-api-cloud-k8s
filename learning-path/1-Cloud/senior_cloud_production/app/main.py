import logging
import os
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.logger import get_logger
from app.database import check_db_connection

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("service_startup", extra={"event": "startup", "version": os.getenv("APP_VERSION", "1.0.0")})
    yield
    logger.info("service_shutdown", extra={"event": "shutdown"})


app = FastAPI(
    title="Senior Cloud API",
    version=os.getenv("APP_VERSION", "1.0.0"),
    docs_url="/docs" if os.getenv("APP_ENV") != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 2)
    logger.info(
        "http_request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": request.client.host if request.client else "unknown",
        },
    )
    return response


@app.get("/", summary="Root")
async def root():
    return {
        "service": os.getenv("APP_NAME", "senior-cloud-api"),
        "status": "online",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "env": os.getenv("APP_ENV", "production"),
    }


@app.get("/health", summary="Health & dependency check")
async def health():
    db_ok, db_msg = await check_db_connection()
    status = 200 if db_ok else 503
    return JSONResponse(
        status_code=status,
        content={
            "status": "healthy" if db_ok else "degraded",
            "checks": {
                "database": {"ok": db_ok, "detail": db_msg},
            },
        },
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
