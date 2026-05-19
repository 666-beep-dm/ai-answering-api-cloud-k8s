"""Basic endpoint tests using pytest + httpx."""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_error():
    """HTTPException(500) must be returned as a proper 500 response."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/error")
    assert r.status_code == 500
    assert "detail" in r.json()


@pytest.mark.asyncio
async def test_slow(anyio_backend):
    # just verify it responds (actual sleep is skipped in test env via monkeypatch)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/slow")
    assert r.status_code == 200
