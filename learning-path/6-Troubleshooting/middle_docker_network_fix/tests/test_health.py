"""
tests/test_health.py
Unit tests for health endpoints.
DB connectivity is mocked so tests run without a real PostgreSQL instance.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_liveness():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_db_health_success():
    healthy_result = {
        "status": "healthy",
        "host": "db",
        "port": 5432,
        "database": "appdb",
        "query": "SELECT 1",
        "result": 1,
    }
    with patch("app.api.health.check_db_connection", new=AsyncMock(return_value=healthy_result)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health/db")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_db_health_failure():
    unhealthy_result = {
        "status": "unhealthy",
        "host": "localhost",
        "port": 5432,
        "database": "appdb",
        "error_type": "OperationalError",
        "error": "Connection refused",
        "hint": "Check DB_HOST value.",
    }
    with patch("app.api.health.check_db_connection", new=AsyncMock(return_value=unhealthy_result)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health/db")
    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "db_host_configured" in response.json()
