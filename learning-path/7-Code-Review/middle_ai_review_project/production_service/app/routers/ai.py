"""production_service/app/routers/ai.py — тонкий роутер без бизнес-логики."""

import logging
from fastapi import APIRouter, Depends
from ..schemas import (
    ChatRequest, ChatResponse,
    HistoryResponse, HistoryItem,
    SummarizeRequest, SummarizeResponse,
    ModelListResponse,
)
from ..dependencies import (
    get_llm_service, get_message_repo, get_summary_repo, verify_api_token
)
from ..llm_service import LLMService
from ..repository import MessageRepository, SummaryRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI"], dependencies=[Depends(verify_api_token)])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    llm: LLMService = Depends(get_llm_service),
    repo: MessageRepository = Depends(get_message_repo),
) -> ChatResponse:
    logger.info("chat request, user_id=%d", payload.user_id)
    text, tokens = await llm.chat(payload.message)
    await repo.save(payload.user_id, payload.message, text)
    return ChatResponse(response=text, tokens_used=tokens)


@router.get("/history", response_model=HistoryResponse)
async def history(
    user_id: int,
    repo: MessageRepository = Depends(get_message_repo),
) -> HistoryResponse:
    rows = await repo.get_by_user(user_id)
    return HistoryResponse(
        user_id=user_id,
        items=[HistoryItem(message=r.message, response=r.response) for r in rows],
    )


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(
    payload: SummarizeRequest,
    llm: LLMService = Depends(get_llm_service),
    repo: SummaryRepository = Depends(get_summary_repo),
) -> SummarizeResponse:
    logger.info("summarize request, chars=%d", len(payload.text))
    text, tokens = await llm.summarize(payload.text)
    await repo.save(payload.text, text)
    return SummarizeResponse(summary=text, tokens_used=tokens)


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    llm: LLMService = Depends(get_llm_service),
) -> ModelListResponse:
    models = await llm.list_models()
    return ModelListResponse(models=models)
