from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Chat
from app.repositories.chat import ChatMemberRepository, ChatRepository
from app.repositories.user import UserRepository


class ChatService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.chats = ChatRepository(session)
        self.members = ChatMemberRepository(session)
        self.users = UserRepository(session)

    async def create_chat(self, *, title: str, is_group: bool, member_ids: list[int]) -> Chat:
        chat = await self.chats.create(title=title, is_group=is_group)
        for user_id in member_ids:
            await self.members.create(chat_id=chat.id, user_id=user_id)
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def update_chat(self, chat: Chat, *, title: str | None = None) -> Chat:
        if title is not None:
            chat.title = title
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def delete_chat(self, chat: Chat) -> None:
        await self.session.delete(chat)
        await self.session.commit()
