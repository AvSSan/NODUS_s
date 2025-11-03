from __future__ import annotations

import json

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Message
from app.repositories.message import MessageRepository

VOICE_REQUIRED_KEYS = {"attachment_id", "duration_ms", "codec"}


class MessageService:
    def __init__(self, session: AsyncSession, redis: Redis):
        self.session = session
        self.redis = redis
        self.messages = MessageRepository(session)

    async def create_message(
        self,
        *,
        chat_id: int,
        author_id: int | None,
        type: str,
        content: str | None,
        payload: dict | None,
    ) -> Message:
        self._validate_payload(type, payload)
        message = await self.messages.create(
            chat_id=chat_id,
            author_id=author_id,
            type=type,
            content=content,
            payload=payload,
        )
        await self.session.commit()
        await self.session.refresh(message)
        await self._publish_event("message.created", message)
        return message

    async def update_message(self, message: Message, *, content: str | None, payload: dict | None) -> Message:
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

    def _validate_payload(self, message_type: str, payload: dict | None) -> None:
        if message_type == "voice":
            if not payload or not VOICE_REQUIRED_KEYS.issubset(payload.keys()):
                missing = VOICE_REQUIRED_KEYS.difference(payload.keys() if payload else set())
                raise ValueError(f"Voice message payload missing keys: {', '.join(sorted(missing))}")

    async def _publish_event(self, event: str, message: Message) -> None:
        payload = {
            "event": event,
            "data": {
                "id": message.id,
                "chat_id": message.chat_id,
                "author_id": message.author_id,
                "type": message.type,
                "content": message.content,
                "payload": message.payload,
                "ts": message.ts.isoformat(),
            },
        }
        await self.redis.publish("ws:messages", json.dumps(payload))
