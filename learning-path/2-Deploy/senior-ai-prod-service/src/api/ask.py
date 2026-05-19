import json
import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src import cache as cache_svc
from src.config import get_settings
from src.db import get_db
from src.metrics import (
    ask_requests_total,
    ask_latency_seconds,
    cache_hits_total,
    cache_misses_total,
    active_streams,
)
from src.models import Conversation
from src.rag.retriever import retrieve
from src.rag.chain import generate_answer, stream_answer
from src.schemas import AskRequest, AskResponse, SourceDocument

logger = logging.getLogger(__name__)
router = APIRouter(tags=["RAG"])


# ── SSE helper ────────────────────────────────────────────────────────────────
async def _sse_stream(question: str, docs, db: AsyncSession, request: AskRequest):
    active_streams.inc()
    t0 = time.perf_counter()
    full_answer: list[str] = []

    try:
        async for token in stream_answer(question, docs):
            full_answer.append(token)
            yield f"data: {json.dumps({'token': token})}\n\n"

        answer = "".join(full_answer)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        # Persist to DB
        record = Conversation(
            id=str(uuid.uuid4()),
            session_id=request.session_id,
            question=question,
            answer=answer,
            num_sources=len(docs),
            latency_ms=elapsed_ms,
            was_cached=False,
        )
        db.add(record)
        await db.commit()

        # Populate semantic cache
        sources = [
            {"content": d.page_content, "metadata": d.metadata, "score": d.metadata.get("retrieval_score", 0.0)}
            for d in docs
        ]
        await cache_svc.set_cached(
            question, {"answer": answer, "sources": sources}
        )

        ask_latency_seconds.observe((time.perf_counter() - t0))
        ask_requests_total.labels(status="success").inc()

        yield f"data: {json.dumps({'done': True, 'latency_ms': elapsed_ms})}\n\n"
    except Exception as exc:
        logger.exception("stream_error: %s", exc)
        ask_requests_total.labels(status="error").inc()
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"
    finally:
        active_streams.dec()


# ── /ask endpoint ─────────────────────────────────────────────────────────────
@router.post("/ask")
async def ask(
    request: AskRequest,
    db: AsyncSession = Depends(get_db),
):
    question = request.question.strip()
    settings = get_settings()

    # 1. Semantic cache check
    cached = await cache_svc.get_cached(question)
    if cached:
        cache_hits_total.inc()
        ask_requests_total.labels(status="cached").inc()
        return AskResponse(
            answer=cached["answer"],
            sources=[SourceDocument(**s) for s in cached.get("sources", [])],
            was_cached=True,
            latency_ms=0.0,
        )
    cache_misses_total.inc()

    # 2. Retrieval
    try:
        docs = await retrieve(question, top_k=request.top_k)
    except Exception as exc:
        logger.exception("retrieval_failed: %s", exc)
        raise HTTPException(status_code=503, detail="Retrieval service unavailable")

    # 3. Streaming or sync response
    if request.stream:
        return StreamingResponse(
            _sse_stream(question, docs, db, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        t0 = time.perf_counter()
        answer = await generate_answer(question, docs)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        sources = [
            SourceDocument(
                content=d.page_content,
                metadata=d.metadata,
                score=d.metadata.get("retrieval_score", 0.0),
            )
            for d in docs
        ]

        record = Conversation(
            id=str(uuid.uuid4()),
            session_id=request.session_id,
            question=question,
            answer=answer,
            num_sources=len(docs),
            latency_ms=elapsed_ms,
            was_cached=False,
        )
        db.add(record)
        await db.commit()

        await cache_svc.set_cached(
            question,
            {"answer": answer, "sources": [s.model_dump() for s in sources]},
        )

        ask_latency_seconds.observe(elapsed_ms / 1000)
        ask_requests_total.labels(status="success").inc()
        return AskResponse(
            answer=answer, sources=sources, was_cached=False, latency_ms=elapsed_ms
        )
