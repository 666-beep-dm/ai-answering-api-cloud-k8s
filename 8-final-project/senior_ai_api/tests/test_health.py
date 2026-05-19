"""Unit test — /api/v1/health endpoint."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_health_returns_200(client):
    with (
        patch("interfaces.api.v1.health_router.redis_hc", new=AsyncMock(return_value=True)),
        patch("interfaces.api.v1.health_router.s3_hc", new=AsyncMock(return_value=True)),
        patch("interfaces.api.v1.health_router.qdrant_hc", new=AsyncMock(return_value=True)),
    ):
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
