from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
        reply_to_id: int | None = None,
    ) -> Message:
        message = Message(
            chat_id=chat_id,
            author_id=author_id,
            type=type,
            content=content,
            payload=payload,
            reply_to_id=reply_to_id,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def list_for_chat(
        self,
        chat_id: int,
        *,
        limit: int = 50,
        before_id: int | None = None,
        include_deleted: bool = False,
    ) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .options(selectinload(Message.reactions))
            .order_by(Message.ts.desc())
            .limit(limit + 1)
        )
        
        if not include_deleted:
            stmt = stmt.where(Message.is_deleted == False)
        
        if before_id is not None:
            cursor_stmt = select(Message.ts).where(Message.id == before_id)
            cursor_ts = await self.session.scalar(cursor_stmt)
            if cursor_ts:
                stmt = stmt.where(Message.ts < cursor_ts)
        
        result = await self.session.scalars(stmt)
        return list(result)

    async def soft_delete(self, message: Message) -> Message:
        message.is_deleted = True
        message.deleted_at = datetime.utcnow()
        message.content = None
        message.payload = None
        await self.session.flush()
        return message

    async def get_with_reactions(self, message_id: int) -> Message | None:
        stmt = (
            select(Message)
            .where(Message.id == message_id)
            .options(selectinload(Message.reactions))
        )
        result = await self.session.scalars(stmt)
        return result.first()
