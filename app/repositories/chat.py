from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.domain.models import Chat, ChatMember
from app.repositories.base import Repository


class ChatRepository(Repository[Chat]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Chat)

    async def get(self, obj_id: int) -> Chat | None:
        """Получить чат с загруженными участниками"""
        stmt = (
            select(Chat)
            .where(Chat.id == obj_id)
            .options(joinedload(Chat.members).joinedload(ChatMember.user))
        )
        result = await self.session.scalars(stmt)
        return result.unique().one_or_none()

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
            .options(joinedload(Chat.members).joinedload(ChatMember.user))
            .order_by(Chat.created_at.desc())
        )
        result = await self.session.scalars(stmt)
        return list(result.unique())

    async def find_direct_message(self, user1_id: int, user2_id: int) -> Chat | None:
        """Найти существующую личную переписку между двумя пользователями"""
        # Проверяем каждый чат вручную, чтобы убедиться, что в нем ровно 2 участника
        result = await self.session.execute(
            select(Chat)
            .where(Chat.is_group == False)
            .options(joinedload(Chat.members).joinedload(ChatMember.user))
        )
        chats = result.scalars().unique().all()
        
        for chat in chats:
            # Получаем членов чата
            members_stmt = select(ChatMember.user_id).where(ChatMember.chat_id == chat.id)
            members_result = await self.session.execute(members_stmt)
            member_ids = {row[0] for row in members_result}
            
            # Проверяем, что в чате ровно эти два пользователя
            if member_ids == {user1_id, user2_id}:
                return chat
        
        return None


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

    async def list_participant_ids(self, chat_id: int) -> list[int]:
        """Получить список user_id всех участников чата"""
        stmt = select(ChatMember.user_id).where(ChatMember.chat_id == chat_id)
        result = await self.session.execute(stmt)
        return [row[0] for row in result]
