from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.models import Conversation
from src.schemas import ConversationRecord

router = APIRouter(prefix="/history", tags=["History"])


@router.get("/", response_model=list[ConversationRecord])
async def get_history(
    session_id: str = Query("default"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.session_id == session_id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
