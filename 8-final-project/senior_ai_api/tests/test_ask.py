"""Unit test — /api/v1/ask endpoint (mock streaming)."""
import pytest
from unittest.mock import AsyncMock, patch


async def _mock_stream(*_, **__):
    for token in ["Hello", " ", "world"]:
        yield token


@pytest.mark.asyncio
async def test_ask_streams_response(client):
    with (
        patch("interfaces.api.v1.ask_router.retrieve", new=AsyncMock(return_value=["context chunk"])),
        patch("interfaces.api.v1.ask_router.stream_answer", new=_mock_stream),
    ):
        resp = await client.post("/api/v1/ask", json={"question": "What is AI?"})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
