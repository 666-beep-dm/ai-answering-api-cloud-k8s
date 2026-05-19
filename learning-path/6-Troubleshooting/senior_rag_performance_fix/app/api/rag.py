"""
app/api/rag.py

Three endpoints demonstrating the full bug → fix → optimized journey:

  POST /ask             ❌ Buggy: blocking I/O + blocking LLM + no timeout
  POST /ask-optimized   ✅ Fixed: async retrieval + async LLM + streaming
  GET  /ask-stream      ✅ Streaming: Server-Sent Events token stream
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.llm_client import call_llm_async, call_llm_blocking, stream_llm_async
from app.core.models import AskRequest, AskResponse, RAGTimings, RetrievedChunk
from app.core.vector_store import rerank, retrieve_async, retrieve_blocking
from app.profiler.timer import PipelineTimer

logger = logging.getLogger("api.rag")
router = APIRouter(tags=["rag"])


# ── ❌ BUGGY endpoint ──────────────────────────────────────────────────
@router.post("/ask", response_model=AskResponse, summary="❌ Buggy RAG (blocking)")
async def ask_buggy(payload: AskRequest) -> AskResponse:
    """
    Demonstrates three bottlenecks:
    1. **Blocking retrieval** (`time.sleep`) stalls the event loop.
    2. **Blocking LLM call** with no timeout hangs the worker thread.
    3. Combined latency (9+ seconds) triggers Nginx's 5s `proxy_read_timeout` → 504.

    Watch the logs for `❌ [BOTTLENECK]` markers.
    """
    timer = PipelineTimer()
    logger.warning("❌ /ask called — entering BUGGY path")

    async with timer.stage("retrieval"):
        # ❌ Bottleneck #1: synchronous blocking call
        raw_chunks = retrieve_blocking(payload.query, payload.top_k)

    async with timer.stage("reranking"):
        ranked = rerank(raw_chunks)

    async with timer.stage("llm_generation"):
        # ❌ Bottleneck #2: blocking LLM call, no timeout
        context = "\n".join(text for text, _ in ranked[:3])
        answer = call_llm_blocking(context, payload.query)

    timings_raw = timer.report()
    logger.warning("❌ /ask complete | timings=%s", json.dumps(timings_raw))

    return AskResponse(
        query=payload.query,
        answer=answer,
        chunks=[RetrievedChunk(text=t, score=s) for t, s in ranked],
        timings=RAGTimings(
            retrieval_time_ms=timings_raw.get("retrieval_time_ms", 0),
            reranking_time_ms=timings_raw.get("reranking_time_ms", 0),
            llm_generation_time_ms=timings_raw.get("llm_generation_time_ms", 0),
            total_time_ms=timings_raw.get("total_time_ms", 0),
        ),
        mode="buggy",
    )


# ── ✅ OPTIMIZED endpoint (non-streaming) ─────────────────────────────
@router.post(
    "/ask-optimized",
    response_model=AskResponse,
    summary="✅ Optimized RAG (async, non-streaming)",
)
async def ask_optimized(payload: AskRequest) -> AskResponse:
    """
    All bottlenecks resolved:
    1. **Async retrieval** via `run_in_executor` — event loop never blocked.
    2. **Async LLM** via `httpx.AsyncClient` with explicit timeout.
    3. Total latency < 500ms → well within Nginx's updated timeout.
    """
    timer = PipelineTimer()
    logger.info("✅ /ask-optimized called")

    async with timer.stage("retrieval"):
        raw_chunks = await retrieve_async(payload.query, payload.top_k)

    async with timer.stage("reranking"):
        ranked = rerank(raw_chunks)

    async with timer.stage("llm_generation"):
        context = "\n".join(text for text, _ in ranked[:3])
        answer = await call_llm_async(context, payload.query)

    timings_raw = timer.report()
    logger.info("✅ /ask-optimized complete | timings=%s", json.dumps(timings_raw))

    return AskResponse(
        query=payload.query,
        answer=answer,
        chunks=[RetrievedChunk(text=t, score=s) for t, s in ranked],
        timings=RAGTimings(
            retrieval_time_ms=timings_raw.get("retrieval_time_ms", 0),
            reranking_time_ms=timings_raw.get("reranking_time_ms", 0),
            llm_generation_time_ms=timings_raw.get("llm_generation_time_ms", 0),
            total_time_ms=timings_raw.get("total_time_ms", 0),
        ),
        mode="optimized",
    )


# ── ✅ STREAMING endpoint (Server-Sent Events) ────────────────────────
@router.post(
    "/ask-stream",
    summary="✅ Optimized RAG with token streaming (SSE)",
    response_class=StreamingResponse,
)
async def ask_stream(payload: AskRequest) -> StreamingResponse:
    """
    **Streaming RAG** — Server-Sent Events.

    First token arrives in ~200ms (TTFT), not 15-20 seconds.
    Requires `proxy_buffering off` in nginx.conf.

    Stream format: `data: <token>\n\n` (SSE protocol).
    Final message: `data: [DONE]\n\n`.
    """
    logger.info("✅ /ask-stream called | query_len=%d", len(payload.query))

    async def event_generator():
        timer = PipelineTimer()

        async with timer.stage("retrieval"):
            raw_chunks = await retrieve_async(payload.query, payload.top_k)

        async with timer.stage("reranking"):
            ranked = rerank(raw_chunks)

        context = "\n".join(text for text, _ in ranked[:3])

        # Emit retrieval metadata first so client can render sources immediately
        meta = {
            "type": "metadata",
            "chunks": [{"text": t[:80], "score": round(s, 4)} for t, s in ranked],
            "retrieval_ms": round(timer._stages["retrieval"].duration_ms, 2),
        }
        yield f"data: {json.dumps(meta)}\n\n"

        # Stream tokens
        token_count = 0
        async with timer.stage("llm_generation"):
            async for token in stream_llm_async(context, payload.query):
                token_count += 1
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

        timings_raw = timer.report()
        done_msg = {
            "type": "done",
            "timings": timings_raw,
            "token_count": token_count,
        }
        logger.info(
            "✅ /ask-stream complete | tokens=%d | timings=%s",
            token_count,
            json.dumps(timings_raw),
        )
        yield f"data: {json.dumps(done_msg)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disables Nginx buffering for this response
        },
    )
