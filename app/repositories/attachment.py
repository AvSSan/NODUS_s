from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Attachment


class AttachmentRepository:
    """Repository для работы с вложениями"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        attachment_id: str,
        user_id: int,
        filename: str,
        content_type: str,
        size_bytes: int,
        storage_key: str,
        metadata: dict | None = None,
        message_id: int | None = None,
    ) -> Attachment:
        """Создает запись о вложении в БД"""
        attachment = Attachment(
            id=attachment_id,
            user_id=user_id,
            message_id=message_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_key=storage_key,
            meta=metadata,
        )
        self.session.add(attachment)
        await self.session.flush()
        return attachment

    async def get_by_id(self, attachment_id: str) -> Attachment | None:
        """Получает вложение по ID"""
        stmt = select(Attachment).where(Attachment.id == attachment_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_message_id(self, message_id: int) -> list[Attachment]:
        """Получает все вложения сообщения"""
        stmt = select(Attachment).where(Attachment.message_id == message_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_message_id(self, attachment_id: str, message_id: int) -> None:
        """Привязывает вложение к сообщению"""
        attachment = await self.get_by_id(attachment_id)
        if attachment:
            attachment.message_id = message_id
            await self.session.flush()

    async def delete(self, attachment_id: str) -> None:
        """Удаляет запись о вложении из БД"""
        attachment = await self.get_by_id(attachment_id)
        if attachment:
            await self.session.delete(attachment)
            await self.session.flush()
