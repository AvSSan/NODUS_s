from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class PresenceService:
    """Сервис для управления онлайн-статусом пользователей"""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def set_user_online(self, user_id: int) -> None:
        """Установить пользователя онлайн"""
        key = f"presence:user:{user_id}"
        await self.redis.setex(key, 300, "online")  # 5 минут TTL
        await self._publish_presence_event(user_id, "online")

    async def set_user_offline(self, user_id: int) -> None:
        """Установить пользователя оффлайн"""
        key = f"presence:user:{user_id}"
        await self.redis.delete(key)
        await self._publish_presence_event(user_id, "offline")

    async def heartbeat(self, user_id: int) -> None:
        """Обновить последнюю активность пользователя (heartbeat)"""
        key = f"presence:user:{user_id}"
        last_seen_key = f"presence:last_seen:{user_id}"
        
        # Обновляем TTL для онлайн статуса
        await self.redis.setex(key, 300, "online")
        
        # Сохраняем время последней активности
        await self.redis.set(last_seen_key, datetime.utcnow().isoformat())

    async def get_user_status(self, user_id: int) -> dict:
        """Получить статус пользователя"""
        key = f"presence:user:{user_id}"
        last_seen_key = f"presence:last_seen:{user_id}"
        
        status = await self.redis.get(key)
        last_seen_str = await self.redis.get(last_seen_key)
        
        last_seen = None
        if last_seen_str:
            if isinstance(last_seen_str, bytes):
                last_seen_str = last_seen_str.decode("utf-8")
            last_seen = datetime.fromisoformat(last_seen_str)
        
        if status:
            if isinstance(status, bytes):
                status = status.decode("utf-8")
            return {"user_id": user_id, "status": status, "last_seen": last_seen}
        else:
            return {"user_id": user_id, "status": "offline", "last_seen": last_seen}

    async def get_multiple_users_status(self, user_ids: list[int]) -> dict[int, dict]:
        """Получить статусы нескольких пользователей"""
        result = {}
        for user_id in user_ids:
            result[user_id] = await self.get_user_status(user_id)
        return result

    async def _publish_presence_event(self, user_id: int, status: str) -> None:
        """Отправить WebSocket событие об изменении статуса"""
        payload = {
            "event": "user.presence",
            "data": {
                "user_id": user_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
        payload_json = json.dumps(payload)
        
        # Публикуем в общий канал присутствия
        await self.redis.publish("presence:updates", payload_json)
        logger.debug(f"Published presence update for user {user_id}: {status}")


class TypingService:
    """Сервис для управления typing indicators"""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def start_typing(self, chat_id: int, user_id: int) -> None:
        """Пользователь начал печатать"""
        key = f"typing:chat:{chat_id}:user:{user_id}"
        await self.redis.setex(key, 10, "typing")  # 10 секунд TTL
        await self._publish_typing_event(chat_id, user_id, True)

    async def stop_typing(self, chat_id: int, user_id: int) -> None:
        """Пользователь перестал печатать"""
        key = f"typing:chat:{chat_id}:user:{user_id}"
        await self.redis.delete(key)
        await self._publish_typing_event(chat_id, user_id, False)

    async def get_typing_users(self, chat_id: int) -> list[int]:
        """Получить список пользователей, которые сейчас печатают в чате"""
        pattern = f"typing:chat:{chat_id}:user:*"
        keys = []
        async for key in self.redis.scan_iter(match=pattern):
            if isinstance(key, bytes):
                key = key.decode("utf-8")
            # Извлекаем user_id из ключа
            user_id = int(key.split(":")[-1])
            keys.append(user_id)
        return keys

    async def _publish_typing_event(self, chat_id: int, user_id: int, is_typing: bool) -> None:
        """Отправить WebSocket событие о наборе текста"""
        payload = {
            "event": "user.typing",
            "data": {
                "chat_id": chat_id,
                "user_id": user_id,
                "is_typing": is_typing,
            },
        }
        payload_json = json.dumps(payload)
        
        # Публикуем в канал чата
        channel = f"chat:{chat_id}:typing"
        await self.redis.publish(channel, payload_json)
        logger.debug(f"Published typing event for user {user_id} in chat {chat_id}: {is_typing}")
