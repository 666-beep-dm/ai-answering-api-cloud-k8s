"""
app/core/vector_store.py

In-memory FAISS-like vector store simulation.
Uses numpy for dot-product similarity; no external service dependency.

Two retrieval interfaces:
  retrieve_blocking()  — ❌ synchronous, blocks event loop (BUG scenario)
  retrieve_async()     — ✅ offloaded to thread pool (FIX scenario)
"""
from __future__ import annotations

import asyncio
import logging
import time
from functools import lru_cache

import numpy as np

from app.core.config import settings

logger = logging.getLogger("vector_store")

# Pre-seeded random corpus — deterministic with a fixed seed
_rng = np.random.default_rng(42)
_CORPUS_VECTORS: np.ndarray = _rng.standard_normal(
    (settings.VECTOR_CORPUS_SIZE, settings.VECTOR_DIM)
).astype(np.float32)
_CORPUS_TEXTS: list[str] = [
    f"Document chunk #{i}: RAG is a technique combining retrieval and generation. "
    f"Relevant information unit {i} from the knowledge base."
    for i in range(settings.VECTOR_CORPUS_SIZE)
]
# Normalize corpus for cosine similarity via dot product
_norms = np.linalg.norm(_CORPUS_VECTORS, axis=1, keepdims=True)
_CORPUS_NORMALIZED = _CORPUS_VECTORS / np.maximum(_norms, 1e-9)


def _encode_query(query: str) -> np.ndarray:
    """Deterministic pseudo-embedding from query hash."""
    rng = np.random.default_rng(abs(hash(query)) % (2**32))
    vec = rng.standard_normal(settings.VECTOR_DIM).astype(np.float32)
    vec /= np.linalg.norm(vec) + 1e-9
    return vec


def _search_corpus(query_vec: np.ndarray, top_k: int) -> list[tuple[str, float]]:
    """Pure CPU dot-product search — CPU-bound work."""
    scores: np.ndarray = _CORPUS_NORMALIZED @ query_vec
    top_indices = np.argpartition(scores, -top_k)[-top_k:]
    top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]
    return [(str(_CORPUS_TEXTS[i]), float(scores[i])) for i in top_indices]


# ── BUG: blocking call ─────────────────────────────────────────────────
def retrieve_blocking(query: str, top_k: int) -> list[tuple[str, float]]:
    """
    ❌ BOTTLENECK #1
    time.sleep() simulates a slow embedding API call (synchronous SDK).
    This BLOCKS the event loop — all other concurrent requests stall.
    """
    logger.warning(
        "❌ [BOTTLENECK] retrieve_blocking called — blocking event loop for %.1fs",
        settings.SIMULATE_BLOCKING_IO_SECONDS,
    )
    time.sleep(settings.SIMULATE_BLOCKING_IO_SECONDS)   # ← blocks event loop!
    return _search_corpus(_encode_query(query), top_k)


# ── FIX: non-blocking ──────────────────────────────────────────────────
async def retrieve_async(query: str, top_k: int) -> list[tuple[str, float]]:
    """
    ✅ FIX for BOTTLENECK #1
    run_in_executor offloads CPU-bound work to a thread pool,
    yielding the event loop back to other coroutines.
    """
    loop = asyncio.get_running_loop()
    await asyncio.sleep(0.05)  # simulates async embedding call (non-blocking)
    results = await loop.run_in_executor(None, _search_corpus, _encode_query(query), top_k)
    return results


# ── Reranking (same for both modes — lightweight) ──────────────────────
def rerank(chunks: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Simple score-based reranking (no external call, pure Python)."""
    return sorted(chunks, key=lambda x: x[1], reverse=True)
