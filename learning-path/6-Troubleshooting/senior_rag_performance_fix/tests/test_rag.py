"""
tests/test_rag.py
Unit tests — mocked LLM and vector store for fast CI execution.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app

PAYLOAD = {"query": "What is RAG?", "top_k": 3}
MOCK_CHUNKS = [("chunk text", 0.9), ("another chunk", 0.8), ("third chunk", 0.7)]
MOCK_ANSWER = "RAG combines retrieval and generation."


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ask_optimized():
    with (
        patch("app.api.rag.retrieve_async", new=AsyncMock(return_value=MOCK_CHUNKS)),
        patch("app.api.rag.call_llm_async", new=AsyncMock(return_value=MOCK_ANSWER)),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/ask-optimized", json=PAYLOAD)
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "optimized"
    assert body["answer"] == MOCK_ANSWER
    assert "timings" in body
    assert body["timings"]["retrieval_time_ms"] >= 0


@pytest.mark.asyncio
async def test_ask_stream():
    with patch("app.api.rag.retrieve_async", new=AsyncMock(return_value=MOCK_CHUNKS)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/ask-stream", json=PAYLOAD)
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    assert "data:" in r.text


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/")
    assert r.status_code == 200
    assert "streaming" in r.json()["endpoints"]
