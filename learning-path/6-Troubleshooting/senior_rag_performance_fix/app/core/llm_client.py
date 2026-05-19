"""
app/core/llm_client.py

LLM client with two modes:
  call_llm_blocking()  — ❌ synchronous requests, no timeout (BUG)
  call_llm_async()     — ✅ async httpx with explicit timeout (FIX)
  stream_llm_async()   — ✅ async streaming, yields tokens (FIX streaming)
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator

import httpx

from app.core.config import settings

logger = logging.getLogger("llm_client")

_MOCK_ANSWER = (
    "Based on the retrieved context, the answer involves understanding "
    "retrieval-augmented generation patterns and optimizing each pipeline stage "
    "for production workloads. The key insight is to decouple retrieval latency "
    "from generation latency using async primitives and streaming responses."
)

_MOCK_TOKENS = _MOCK_ANSWER.split()


# ── BUG: blocking sync call, no timeout ───────────────────────────────
def call_llm_blocking(context: str, query: str) -> str:
    """
    ❌ BOTTLENECK #2
    Synchronous requests.get() with NO timeout.
    If the LLM API is slow (15-20s), this worker thread hangs indefinitely.
    Combined with Nginx's 5s proxy_read_timeout → 504 Gateway Timeout.
    """
    logger.warning(
        "❌ [BOTTLENECK] call_llm_blocking — no timeout, sleeping %.1fs to simulate LLM latency",
        settings.SIMULATE_LLM_DELAY_SECONDS,
    )
    # Simulate slow LLM using blocking sleep (not asyncio.sleep!)
    time.sleep(settings.SIMULATE_LLM_DELAY_SECONDS)   # ← blocks event loop!

    # In a real bug scenario this would be:
    # import requests
    # response = requests.get(settings.LLM_API_URL)  # no timeout!
    return _MOCK_ANSWER


# ── FIX: async httpx with timeout ─────────────────────────────────────
async def call_llm_async(context: str, query: str) -> str:
    """
    ✅ FIX for BOTTLENECK #2
    httpx.AsyncClient with explicit timeout — never hangs indefinitely.
    Falls back to mock answer if the real LLM service is unavailable.
    """
    logger.info("✅ [FIX] call_llm_async | timeout=%.1fs", settings.LLM_TIMEOUT_FIX)
    try:
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_FIX) as client:
            response = await client.post(
                settings.LLM_API_URL,
                json={"context": context[:1000], "query": query},
            )
            response.raise_for_status()
            return response.json().get("answer", _MOCK_ANSWER)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
        logger.warning("LLM API unavailable (%s) — using mock answer", type(exc).__name__)
        await asyncio.sleep(0.1)  # minimal async yield
        return _MOCK_ANSWER


# ── FIX: streaming tokens ──────────────────────────────────────────────
async def stream_llm_async(context: str, query: str) -> AsyncIterator[str]:
    """
    ✅ FIX — Streaming response.
    Yields tokens one-by-one so the client receives the first token
    in ~200ms (TTFT) instead of waiting 15-20s for the full response.
    """
    logger.info("✅ [STREAMING] stream_llm_async started")
    for i, token in enumerate(_MOCK_TOKENS):
        await asyncio.sleep(0.04)  # 40ms per token → smooth streaming
        yield token + (" " if i < len(_MOCK_TOKENS) - 1 else "")
    logger.info("✅ [STREAMING] stream_llm_async complete | tokens=%d", len(_MOCK_TOKENS))
