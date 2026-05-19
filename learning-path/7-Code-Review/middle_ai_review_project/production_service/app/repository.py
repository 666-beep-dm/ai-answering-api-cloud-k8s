"""production_service/app/repository.py
Repository layer — единственный слой, который знает о SQL.
Использует параметризованные запросы (защита от SQL-инъекций).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Message, Summary


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, user_id: int, message: str, response: str) -> Message:
        obj = Message(user_id=user_id, message=message, response=response)
        self._session.add(obj)
        await self._session.flush()
        return obj

    async def get_by_user(self, user_id: int) -> list[Message]:
        result = await self._session.execute(
            select(Message)
            .where(Message.user_id == user_id)
            .order_by(Message.created_at.desc())
            .limit(50)
        )
        return list(result.scalars().all())


class SummaryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, text: str, summary: str) -> Summary:
        obj = Summary(text=text, summary=summary)
        self._session.add(obj)
        await self._session.flush()
        return obj
