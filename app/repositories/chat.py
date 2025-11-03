from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Chat, ChatMember
from app.repositories.base import Repository


class ChatRepository(Repository[Chat]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Chat)

    async def create(self, *, title: str, is_group: bool) -> Chat:
        chat = Chat(title=title, is_group=is_group)
        self.session.add(chat)
        await self.session.flush()
        return chat

    async def list_for_user(self, user_id: int) -> list[Chat]:
        stmt = (
            select(Chat)
            .join(ChatMember)
            .where(ChatMember.user_id == user_id)
            .order_by(Chat.created_at.desc())
        )
        result = await self.session.scalars(stmt)
        return list(result)


class ChatMemberRepository(Repository[ChatMember]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ChatMember)

    async def create(self, *, chat_id: int, user_id: int, role: str = "member") -> ChatMember:
        member = ChatMember(chat_id=chat_id, user_id=user_id, role=role)
        self.session.add(member)
        await self.session.flush()
        return member

    async def get_member(self, chat_id: int, user_id: int) -> ChatMember | None:
        stmt = select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id)
        result = await self.session.scalars(stmt)
        return result.one_or_none()
