"""
Test endpoints covering all observable scenarios.
Designed to generate varied telemetry for dashboard / alert testing.
"""
from __future__ import annotations

import asyncio
import random

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, field_validator

from app.observability.tracer import start_span, current_trace_id, current_span_id
from app.observability.metrics import metrics_output
from app.core.config import get_settings

_settings = get_settings()
router    = APIRouter(tags=["Observability Test Endpoints"])


# ── /health ───────────────────────────────────────────────────────────────
@router.get("/health", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok"}


# ── /metrics ──────────────────────────────────────────────────────────────
@router.get(_settings.metrics_path, include_in_schema=False)
async def metrics_endpoint() -> Response:
    body, ct = metrics_output()
    return Response(content=body, media_type=ct)


# ── /api/v1/success ───────────────────────────────────────────────────────
@router.get("/api/v1/success", summary="200 OK — happy path")
async def success(request: Request) -> dict:
    with start_span("success_handler",
                    attributes={"request_id": request.headers.get("x-request-id", "")}):
        return {
            "status":     "ok",
            "trace_id":   current_trace_id(),
            "span_id":    current_span_id(),
            "message":    "Request processed successfully.",
        }


# ── /api/v1/slow ──────────────────────────────────────────────────────────
@router.get("/api/v1/slow", summary="Variable latency (50–800 ms)")
async def slow_endpoint() -> dict:
    delay_ms = random.randint(50, 800)
    with start_span("slow_handler", attributes={"simulated_delay_ms": delay_ms}):
        await asyncio.sleep(delay_ms / 1000)
    return {
        "status":        "ok",
        "delay_ms":      delay_ms,
        "trace_id":      current_trace_id(),
    }


# ── /api/v1/client-error ─────────────────────────────────────────────────
@router.get("/api/v1/client-error", summary="400 Bad Request")
async def client_error() -> None:
    raise HTTPException(
        status_code=400,
        detail="Bad Request: missing required parameter 'resource_id'.",
    )


# ── /api/v1/server-error ─────────────────────────────────────────────────
@router.get("/api/v1/server-error", summary="500 — ZeroDivisionError + stack trace")
async def server_error() -> None:
    with start_span("server_error_handler"):
        _ = 1 / 0  # noqa: F841


# ── /api/v1/validate ─────────────────────────────────────────────────────
class Item(BaseModel):
    name:  str
    price: float

    @field_validator("price")
    @classmethod
    def positive_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("price must be positive")
        return v


@router.post("/api/v1/validate", summary="Pydantic 422 validation demo")
async def validate_item(item: Item) -> dict:
    return {"received": item.model_dump(), "trace_id": current_trace_id()}
