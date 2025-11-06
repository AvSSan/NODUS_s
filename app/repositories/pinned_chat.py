from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.domain.models import Chat, ChatMember, PinnedChat
from app.repositories.base import Repository


class PinnedChatRepository(Repository[PinnedChat]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, PinnedChat)

    async def create(self, *, user_id: int, chat_id: int, pin_order: int) -> PinnedChat:
        """Закрепить чат"""
        pinned = PinnedChat(user_id=user_id, chat_id=chat_id, pin_order=pin_order)
        self.session.add(pinned)
        await self.session.flush()
        return pinned

    async def get_pinned(self, user_id: int, chat_id: int) -> PinnedChat | None:
        """Получить информацию о закреплении чата"""
        stmt = select(PinnedChat).where(
            PinnedChat.user_id == user_id,
            PinnedChat.chat_id == chat_id
        )
        result = await self.session.scalars(stmt)
        return result.first()

    async def count_pinned(self, user_id: int) -> int:
        """Получить количество закрепленных чатов пользователя"""
        stmt = select(func.count()).select_from(PinnedChat).where(PinnedChat.user_id == user_id)
        result = await self.session.scalar(stmt)
        return result or 0

    async def get_max_pin_order(self, user_id: int) -> int:
        """Получить максимальный порядок закрепления"""
        stmt = select(func.max(PinnedChat.pin_order)).where(PinnedChat.user_id == user_id)
        result = await self.session.scalar(stmt)
        return result or 0

    async def list_pinned_chats(self, user_id: int) -> list[Chat]:
        """
        Получить список закрепленных чатов пользователя,
        отсортированных по порядку закрепления.
        """
        stmt = (
            select(Chat)
            .join(PinnedChat)
            .where(PinnedChat.user_id == user_id)
            .options(joinedload(Chat.members).joinedload(ChatMember.user))
            .order_by(PinnedChat.pin_order)
        )
        result = await self.session.scalars(stmt)
        return list(result.unique())

    async def unpin(self, pinned_chat: PinnedChat) -> None:
        """Открепить чат"""
        await self.session.delete(pinned_chat)
        await self.session.flush()

    async def reorder_pins(self, user_id: int) -> None:
        """
        Переупорядочить закрепленные чаты после удаления одного из них,
        чтобы pin_order шел последовательно без пробелов.
        """
        stmt = (
            select(PinnedChat)
            .where(PinnedChat.user_id == user_id)
            .order_by(PinnedChat.pin_order)
        )
        result = await self.session.scalars(stmt)
        pinned_chats = list(result)
        
        for idx, pinned in enumerate(pinned_chats):
            pinned.pin_order = idx
        
        await self.session.flush()
