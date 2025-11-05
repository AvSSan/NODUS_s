from __future__ import annotations

import json
import logging

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import Message, MessageReaction
from app.repositories.chat import ChatMemberRepository
from app.repositories.message import MessageRepository
from app.repositories.message_read import MessageReadRepository
from app.repositories.message_reaction import MessageReactionRepository

VOICE_REQUIRED_KEYS = {"attachment_id", "duration_ms", "codec"}

logger = logging.getLogger(__name__)


class MessageService:
    def __init__(self, session: AsyncSession, redis: Redis):
        self.session = session
        self.redis = redis
        self.messages = MessageRepository(session)
        self.chat_members = ChatMemberRepository(session)
        self.message_reads = MessageReadRepository(session)
        self.reactions = MessageReactionRepository(session)

    async def create_message(
        self,
        *,
        chat_id: int,
        author_id: int | None,
        type: str,
        content: str | None,
        payload: dict | None,
        reply_to_id: int | None = None,
    ) -> Message:
        self._validate_payload(type, payload)
        
        # Проверка существования сообщения, на которое отвечаем
        if reply_to_id is not None:
            reply_message = await self.messages.get(reply_to_id)
            if not reply_message or reply_message.chat_id != chat_id:
                raise ValueError("Reply message not found or belongs to different chat")
        
        message = await self.messages.create(
            chat_id=chat_id,
            author_id=author_id,
            type=type,
            content=content,
            payload=payload,
            reply_to_id=reply_to_id,
        )
        message.status = "delivered"
        await self.session.commit()
        # Явная загрузка reactions для избежания ошибки MissingGreenlet при сериализации
        await self.session.refresh(message, ["reactions"])
        await self._publish_event("message.created", message)
        return message

    async def update_message(self, message: Message, *, content: str | None, payload: dict | None) -> Message:
        if message.is_deleted:
            raise ValueError("Cannot update deleted message")
        
        if payload is not None:
            self._validate_payload(message.type, payload)
        if content is not None:
            message.content = content
        if payload is not None:
            message.payload = payload
        await self.session.commit()
        await self.session.refresh(message)
        await self._publish_event("message.updated", message)
        return message

    async def delete_message(self, message: Message) -> Message:
        """Мягкое удаление сообщения"""
        if message.is_deleted:
            raise ValueError("Message already deleted")
        
        message = await self.messages.soft_delete(message)
        await self.session.commit()
        await self.session.refresh(message)
        await self._publish_event("message.deleted", message)
        return message

    async def add_reaction(self, message_id: int, user_id: int, emoji: str) -> MessageReaction:
        """Добавить реакцию на сообщение"""
        # Проверяем существование реакции
        existing = await self.reactions.get_user_reaction(
            message_id=message_id, user_id=user_id, emoji=emoji
        )
        if existing:
            raise ValueError("Reaction already exists")
        
        reaction = await self.reactions.add_reaction(
            message_id=message_id, user_id=user_id, emoji=emoji
        )
        await self.session.commit()
        await self.session.refresh(reaction)
        
        # Получаем сообщение для определения участников чата
        message = await self.messages.get(message_id)
        if message:
            await self._publish_reaction_event("reaction.added", message.chat_id, reaction)
        
        return reaction

    async def remove_reaction(self, message_id: int, user_id: int, emoji: str) -> bool:
        """Удалить реакцию с сообщения"""
        # Получаем сообщение для определения участников чата
        message = await self.messages.get(message_id)
        if not message:
            return False
        
        success = await self.reactions.remove_reaction(
            message_id=message_id, user_id=user_id, emoji=emoji
        )
        
        if success:
            await self.session.commit()
            await self._publish_reaction_event(
                "reaction.removed",
                message.chat_id,
                {"message_id": message_id, "user_id": user_id, "emoji": emoji},
            )
        
        return success

    def _validate_payload(self, message_type: str, payload: dict | None) -> None:
        if message_type == "voice":
            if not payload or not VOICE_REQUIRED_KEYS.issubset(payload.keys()):
                missing = VOICE_REQUIRED_KEYS.difference(payload.keys() if payload else set())
                raise ValueError(f"Voice message payload missing keys: {', '.join(sorted(missing))}")

    async def _publish_event(self, event: str, message: Message) -> None:
        """Отправить WebSocket событие всем участникам чата"""
        # Получаем всех участников чата
        participant_ids = await self.chat_members.list_participant_ids(message.chat_id)
        
        # Формируем payload события
        payload = {
            "event": event,
            "data": {
                "id": message.id,
                "chat_id": message.chat_id,
                "author_id": message.author_id,
                "type": message.type,
                "content": message.content,
                "payload": message.payload,
                "status": message.status,
                "ts": message.ts.isoformat(),
                "reply_to_id": message.reply_to_id,
                "is_deleted": message.is_deleted,
                "deleted_at": message.deleted_at.isoformat() if message.deleted_at else None,
                "updated_at": message.updated_at.isoformat() if message.updated_at else None,
            },
        }
        payload_json = json.dumps(payload)
        
        # Отправляем событие в персональный канал каждого участника
        for user_id in participant_ids:
            channel = f"ws:user:{user_id}"
            await self.redis.publish(channel, payload_json)
            logger.debug(f"Published {event} to user {user_id} for message {message.id}")
        
        logger.info(f"Broadcast {event} to {len(participant_ids)} participants in chat {message.chat_id}")

    async def _publish_reaction_event(self, event: str, chat_id: int, data) -> None:
        """Отправить WebSocket событие о реакции всем участникам чата"""
        participant_ids = await self.chat_members.list_participant_ids(chat_id)
        
        # Формируем payload для реакции
        if isinstance(data, MessageReaction):
            payload = {
                "event": event,
                "data": {
                    "id": data.id,
                    "message_id": data.message_id,
                    "user_id": data.user_id,
                    "emoji": data.emoji,
                    "created_at": data.created_at.isoformat(),
                },
            }
        else:
            payload = {"event": event, "data": data}
        
        payload_json = json.dumps(payload)
        
        for user_id in participant_ids:
            channel = f"ws:user:{user_id}"
            await self.redis.publish(channel, payload_json)
            logger.debug(f"Published {event} to user {user_id}")
        
        logger.info(f"Broadcast {event} to {len(participant_ids)} participants in chat {chat_id}")

    async def mark_messages_as_read(self, chat_id: int, user_id: int) -> list[int]:
        """
        Отметить все непрочитанные сообщения в чате как прочитанные для пользователя.
        Возвращает список ID прочитанных сообщений.
        """
        logger.info(f"\n========== MARK AS READ START ==========")
        logger.info(f"Chat ID: {chat_id}, User ID: {user_id}")
        
        # Получаем ID всех непрочитанных сообщений
        unread_message_ids = await self.message_reads.get_unread_message_ids(chat_id, user_id)
        
        logger.info(f"Unread messages found: {len(unread_message_ids)} - IDs: {unread_message_ids}")
        
        if not unread_message_ids:
            logger.info(f"No unread messages, exiting")
            logger.info(f"========== MARK AS READ END ==========\n")
            return []
        
        # Отмечаем каждое сообщение как прочитанное в таблице message_reads
        for message_id in unread_message_ids:
            await self.message_reads.mark_as_read(message_id, user_id)
        
        # Обновляем статус сообщений на "read" в таблице messages
        # Если ВСЕ участники чата прочитали сообщение
        from app.domain.models import Message
        from sqlalchemy import select, update
        
        # Получаем количество участников чата
        participant_ids = await self.chat_members.list_participant_ids(chat_id)
        total_participants = len(participant_ids)
        
        # Список сообщений, у которых изменился статус на "read"
        updated_messages = []
        
        # Для каждого сообщения проверяем, прочитали ли его все участники (кроме автора)
        for message_id in unread_message_ids:
            message = await self.messages.get(message_id)
            if not message:
                logger.warning(f"Message {message_id} not found, skipping")
                continue
            
            logger.info(f"Checking message {message_id}:")
            logger.info(f"  Current status: {message.status}")
            logger.info(f"  Author ID: {message.author_id}")
            
            # Считаем количество прочтений
            from app.domain.models import MessageRead
            stmt = select(MessageRead).where(MessageRead.message_id == message_id)
            result = await self.session.scalars(stmt)
            read_count = len(list(result))
            
            # Если все прочитали (участники минус автор = read_count)
            expected_reads = total_participants - 1 if message.author_id in participant_ids else total_participants
            
            logger.info(f"  Read count: {read_count}/{expected_reads}")
            
            if read_count >= expected_reads:
                old_status = message.status
                message.status = "read"
                updated_messages.append(message)
                logger.info(f"  ✅ Status changed: {old_status} -> read")
            else:
                logger.info(f"  ⏳ Not all participants read yet, keeping status: {message.status}")
        
        await self.session.commit()
        
        # Обновляем сообщения после коммита
        for message in updated_messages:
            await self.session.refresh(message)
        
        # Отправляем WebSocket событие всем участникам чата с обновленными сообщениями
        await self._publish_read_event(chat_id, unread_message_ids, updated_messages)
        
        logger.info(f"Marked {len(unread_message_ids)} messages as read in chat {chat_id} for user {user_id}, {len(updated_messages)} changed to 'read'")
        return unread_message_ids

    async def _publish_read_event(self, chat_id: int, message_ids: list[int], updated_messages: list) -> None:
        """Отправить WebSocket событие о прочитанных сообщениях всем участникам чата"""
        logger.info(f"\n========== WEBSOCKET PUBLISH START ==========")
        logger.info(f"Chat ID: {chat_id}")
        logger.info(f"Message IDs: {message_ids}")
        logger.info(f"Updated messages (status changed to 'read'): {len(updated_messages)}")
        
        # Получаем всех участников чата
        participant_ids = await self.chat_members.list_participant_ids(chat_id)
        logger.info(f"Participants: {participant_ids}")
        
        # Отправляем событие message.updated для каждого сообщения с обновленным статусом
        for message in updated_messages:
            logger.info(f"\nSending message.updated for message {message.id}:")
            logger.info(f"  Status: {message.status}")
            logger.info(f"  Content: {message.content[:30] if message.content else 'None'}...")
            
            payload = {
                "event": "message.updated",
                "data": {
                    "id": message.id,
                    "chat_id": message.chat_id,
                    "author_id": message.author_id,
                    "type": message.type,
                    "content": message.content,
                    "payload": message.payload,
                    "status": message.status,
                    "ts": message.ts.isoformat(),
                },
            }
            payload_json = json.dumps(payload)
            
            # Отправляем всем участникам
            for user_id in participant_ids:
                channel = f"ws:user:{user_id}"
                await self.redis.publish(channel, payload_json)
                logger.info(f"  ✅ Published to user {user_id} on channel {channel}")
        
        # Также отправляем обобщенное событие message.read для совместимости
        logger.info(f"\nSending message.read event:")
        payload = {
            "event": "message.read",
            "data": {
                "chat_id": chat_id,
                "message_ids": message_ids,
            },
        }
        payload_json = json.dumps(payload)
        
        for user_id in participant_ids:
            channel = f"ws:user:{user_id}"
            await self.redis.publish(channel, payload_json)
            logger.info(f"  ✅ Published to user {user_id}")
        
        logger.info(f"\n✅ TOTAL: Sent {len(updated_messages)} message.updated + 1 message.read to {len(participant_ids)} participants")
        logger.info(f"========== WEBSOCKET PUBLISH END ==========\n")
