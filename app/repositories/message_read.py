from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import MessageRead
from app.repositories.base import Repository


class MessageReadRepository(Repository[MessageRead]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, MessageRead)

    async def mark_as_read(self, message_id: int, user_id: int) -> MessageRead:
        """Отметить сообщение как прочитанное. Если уже отмечено - вернуть существующую запись."""
        # Проверяем, не было ли уже отмечено
        stmt = select(MessageRead).where(
            MessageRead.message_id == message_id,
            MessageRead.user_id == user_id
        )
        result = await self.session.scalar(stmt)
        
        if result is not None:
            return result
        
        # Создаем новую запись
        message_read = MessageRead(message_id=message_id, user_id=user_id)
        self.session.add(message_read)
        await self.session.flush()
        return message_read

    async def get_unread_message_ids(self, chat_id: int, user_id: int) -> list[int]:
        """Получить ID всех непрочитанных сообщений в чате для пользователя"""
        from app.domain.models import Message
        
        # Подзапрос для прочитанных сообщений
        read_subquery = select(MessageRead.message_id).where(
            MessageRead.user_id == user_id
        ).subquery()
        
        # Получаем ID сообщений, которые НЕ прочитаны пользователем
        # И которые НЕ написаны этим пользователем (свои сообщения не считаются непрочитанными)
        stmt = select(Message.id).where(
            Message.chat_id == chat_id,
            Message.author_id != user_id,
            Message.id.not_in(select(read_subquery))
        )
        
        result = await self.session.scalars(stmt)
        return list(result)
