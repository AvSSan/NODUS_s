from __future__ import annotations

import json
import logging

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Chat
from app.repositories.chat import ChatMemberRepository, ChatRepository
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, session: AsyncSession, redis: Redis | None = None):
        self.session = session
        self.redis = redis
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

    async def delete_chat(self, chat: Chat, deleted_by: int) -> None:
        """Удалить чат и отправить WebSocket событие всем участникам"""
        chat_id = chat.id
        
        # Получаем список участников ДО удаления чата
        participant_ids = await self.members.list_participant_ids(chat_id)
        
        # Удаляем чат
        await self.session.delete(chat)
        await self.session.commit()
        
        # Отправляем WebSocket событие всем участникам
        if self.redis:
            await self._publish_chat_deleted_event(chat_id, deleted_by, participant_ids)
        else:
            logger.warning(f"Redis not available, chat.deleted event not sent for chat {chat_id}")

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

    async def _publish_chat_deleted_event(
        self, chat_id: int, deleted_by: int, participant_ids: list[int]
    ) -> None:
        """Отправить WebSocket событие chat.deleted всем участникам чата"""
        payload = {
            "event": "chat.deleted",
            "data": {
                "id": chat_id,
                "deleted_by": deleted_by,
            },
        }
        payload_json = json.dumps(payload)
        
        # Отправляем событие в персональный канал каждого участника
        for user_id in participant_ids:
            channel = f"ws:user:{user_id}"
            await self.redis.publish(channel, payload_json)
            logger.debug(f"Published chat.deleted to user {user_id} for chat {chat_id}")
        
        logger.info(f"Broadcast chat.deleted to {len(participant_ids)} participants for chat {chat_id}")
