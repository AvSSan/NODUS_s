from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import MessageReaction
from app.repositories.base import Repository


class MessageReactionRepository(Repository[MessageReaction]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, MessageReaction)

    async def add_reaction(self, *, message_id: int, user_id: int, emoji: str) -> MessageReaction:
        """Добавить реакцию на сообщение"""
        reaction = MessageReaction(message_id=message_id, user_id=user_id, emoji=emoji)
        self.session.add(reaction)
        await self.session.flush()
        return reaction

    async def remove_reaction(self, *, message_id: int, user_id: int, emoji: str) -> bool:
        """Удалить реакцию с сообщения"""
        stmt = delete(MessageReaction).where(
            MessageReaction.message_id == message_id,
            MessageReaction.user_id == user_id,
            MessageReaction.emoji == emoji,
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def get_message_reactions(self, message_id: int) -> list[MessageReaction]:
        """Получить все реакции для сообщения"""
        stmt = select(MessageReaction).where(MessageReaction.message_id == message_id)
        result = await self.session.scalars(stmt)
        return list(result)

    async def get_user_reaction(
        self, *, message_id: int, user_id: int, emoji: str
    ) -> MessageReaction | None:
        """Получить конкретную реакцию пользователя"""
        stmt = select(MessageReaction).where(
            MessageReaction.message_id == message_id,
            MessageReaction.user_id == user_id,
            MessageReaction.emoji == emoji,
        )
        result = await self.session.scalars(stmt)
        return result.first()
