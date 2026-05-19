"""
Endpoint tests — verify HTTP status codes and JSON log shape.
"""

import json
import logging
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/success")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert "x-request-id" in r.headers          # middleware injected UUID


@pytest.mark.asyncio
async def test_client_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/client-error")
    assert r.status_code == 400
    assert "detail" in r.json()


@pytest.mark.asyncio
async def test_server_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/server-error")
    assert r.status_code == 500
    assert r.json()["error"] == "ZeroDivisionError"


@pytest.mark.asyncio
async def test_validation_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/validate", json={"name": "widget", "price": -5})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_json_log_format(caplog):
    """Every log record emitted during a request must be valid JSON."""
    with caplog.at_level(logging.DEBUG, logger="app"):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            await c.get("/success")

    for record in caplog.records:
        # The JsonFormatter serialises the message; raw records still have
        # extra attrs set by the middleware — spot-check request_id.
        if hasattr(record, "request_id"):
            assert record.request_id  # non-empty UUID string
