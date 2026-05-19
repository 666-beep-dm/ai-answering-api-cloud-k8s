import asyncio
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.middleware import LoggingMiddleware

app = FastAPI(
    title="FastAPI Logging Middleware",
    description="Junior-level project demonstrating request logging via Middleware.",
    version="1.0.0",
)

# Register custom middleware
app.add_middleware(LoggingMiddleware)


# ── Endpoints ──────────────────────────────────────────────────────────

@app.get("/", summary="Health check", tags=["General"])
async def root():
    """Simple health-check endpoint."""
    return {"status": "ok", "message": "FastAPI Logging Middleware is running."}


@app.get("/slow", summary="Slow endpoint (2 s delay)", tags=["General"])
async def slow_endpoint():
    """Simulates a slow operation with asyncio.sleep to test duration logging."""
    await asyncio.sleep(2)
    return {"status": "ok", "message": "Slow response after 2 seconds."}


@app.get("/error", summary="Simulated 500 error", tags=["General"])
async def error_endpoint():
    """Always raises an HTTP 500 to verify error-status logging."""
    raise HTTPException(status_code=500, detail="Simulated internal server error.")
