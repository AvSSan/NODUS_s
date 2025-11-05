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
        # Перезагружаем чат с участниками
        chat = await self.chats.get(chat.id)
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

    async def create_or_get_direct_message(self, user1_id: int, user2_id: int) -> Chat:
        """Создать или получить существующую личную переписку между двумя пользователями"""
        if user1_id == user2_id:
            raise ValueError("Cannot create direct message with yourself")
        
        # Проверяем, существует ли уже личная переписка
        existing_dm = await self.chats.find_direct_message(user1_id, user2_id)
        if existing_dm:
            return existing_dm
        
        # Проверяем, что оба пользователя существуют
        user1 = await self.users.get(user1_id)
        user2 = await self.users.get(user2_id)
        if not user1 or not user2:
            raise ValueError("One or both users not found")
        
        # Создаем новую личную переписку
        # Заголовок для личной переписки обычно пустой или содержит имя собеседника
        title = f"{user1.display_name} & {user2.display_name}"
        chat = await self.chats.create(title=title, is_group=False)
        
        # Добавляем обоих пользователей как участников
        await self.members.create(chat_id=chat.id, user_id=user1_id, role="member")
        await self.members.create(chat_id=chat.id, user_id=user2_id, role="member")
        
        await self.session.commit()
        # Перезагружаем чат с участниками
        chat = await self.chats.get(chat.id)
        return chat
