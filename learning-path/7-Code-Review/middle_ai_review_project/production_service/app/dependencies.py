"""production_service/app/dependencies.py — FastAPI dependency injection."""

import logging
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from .config import get_settings, Settings
from .database import get_db
from .llm_service import LLMService
from .repository import MessageRepository, SummaryRepository

logger = logging.getLogger(__name__)


def get_llm_service(settings: Settings = Depends(get_settings)) -> LLMService:
    return LLMService(settings)


def get_message_repo(session: AsyncSession = Depends(get_db)) -> MessageRepository:
    return MessageRepository(session)


def get_summary_repo(session: AsyncSession = Depends(get_db)) -> SummaryRepository:
    return SummaryRepository(session)


async def verify_api_token(
    x_api_token: str = Header(...),
    settings: Settings = Depends(get_settings),
) -> None:
    """Проверяет API-токен из заголовка запроса."""
    if x_api_token != settings.api_token_secret:
        logger.warning("Unauthorized request with invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
        )
