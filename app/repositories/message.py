from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Message
from app.repositories.base import Repository


class MessageRepository(Repository[Message]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Message)

    async def create(
        self,
        *,
        chat_id: int,
        author_id: int | None,
        type: str,
        content: str | None,
        payload: dict | None,
    ) -> Message:
        message = Message(chat_id=chat_id, author_id=author_id, type=type, content=content, payload=payload)
        self.session.add(message)
        await self.session.flush()
        return message

    async def list_for_chat(self, chat_id: int, *, limit: int = 50, before_id: int | None = None) -> list[Message]:
        stmt = select(Message).where(Message.chat_id == chat_id).order_by(Message.ts.desc()).limit(limit)
        if before_id is not None:
            stmt = stmt.where(Message.id < before_id)
        result = await self.session.scalars(stmt)
        return list(result)
