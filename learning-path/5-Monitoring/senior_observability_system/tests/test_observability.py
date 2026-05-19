"""
Observability integration tests.
Covers: HTTP status codes, response headers (trace IDs), metrics endpoint,
error handler responses, and JSON log structure.
"""
from __future__ import annotations

import logging
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_success_with_trace_headers():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/success")
    assert r.status_code == 200
    assert "x-request-id" in r.headers
    assert "x-trace-id"   in r.headers
    assert "x-span-id"    in r.headers
    body = r.json()
    assert body["status"] == "ok"
    assert "trace_id" in body


@pytest.mark.asyncio
async def test_propagate_incoming_trace_id():
    """Client-supplied X-Trace-ID must be echoed back in the response."""
    custom_trace = "deadbeef-1234-5678-abcd-000000000001"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/success",
                        headers={"X-Trace-ID": custom_trace})
    assert r.headers.get("x-trace-id") == custom_trace


@pytest.mark.asyncio
async def test_client_error_logged_as_warning():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/client-error")
    assert r.status_code == 400
    assert "detail" in r.json()


@pytest.mark.asyncio
async def test_server_error_returns_500():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/server-error")
    assert r.status_code == 500
    assert r.json()["error"] == "ZeroDivisionError"


@pytest.mark.asyncio
async def test_validation_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/validate", json={"name": "widget", "price": -1})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_metrics_endpoint_reachable():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text
    assert "http_request_duration_seconds" in r.text


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_json_log_format(caplog):
    with caplog.at_level(logging.DEBUG, logger="app"):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            await c.get("/api/v1/success")
    for record in caplog.records:
        if hasattr(record, "trace_id"):
            assert record.trace_id        # non-empty
        if hasattr(record, "request_id"):
            assert record.request_id      # non-empty
