"""POST /api/v1/ask — SSE streaming response."""
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from core.logging import get_logger, trace_id_var
from domain.services.llm_service import stream_answer
from domain.services.rag_service import retrieve
from interfaces.api.v1.schemas import QuestionRequest

router = APIRouter()
logger = get_logger(__name__)


async def _event_stream(question: str) -> AsyncIterator[bytes]:
    chunks = await retrieve(question)
    logger.info(f"Retrieved {len(chunks)} context chunks.")

    full = []
    async for token in stream_answer(question, chunks):
        full.append(token)
        payload = json.dumps({"token": token, "trace_id": trace_id_var.get()})
        yield f"data: {payload}\n\n".encode()

    yield b"data: [DONE]\n\n"
    logger.info(f"Stream complete. total_tokens={len(full)}")


@router.post("")
async def ask(body: QuestionRequest) -> StreamingResponse:
    logger.info(f"Question: {body.question[:80]}")
    return StreamingResponse(
        _event_stream(body.question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
