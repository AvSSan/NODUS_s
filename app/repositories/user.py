from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import User
from app.repositories.base import Repository


class UserRepository(Repository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.scalars(stmt)
        return result.one_or_none()

    async def get_by_tag(self, tag: str) -> User | None:
        """Получить пользователя по тегу"""
        stmt = select(User).where(User.tag == tag.lower())
        result = await self.session.scalars(stmt)
        return result.one_or_none()

    async def is_tag_available(self, tag: str, exclude_user_id: int | None = None) -> bool:
        """Проверить, доступен ли тег"""
        stmt = select(User).where(User.tag == tag.lower())
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)
        result = await self.session.scalars(stmt)
        return result.one_or_none() is None

    def generate_initial_tag(self, email: str, user_id: int) -> str:
        """Генерировать начальный тег из email и id пользователя"""
        # Извлекаем часть email до @
        email_part = email.split('@')[0]
        # Удаляем все кроме букв, цифр и подчеркиваний
        email_part = re.sub(r'[^a-zA-Z0-9_]', '', email_part)
        # Обрезаем до разумной длины и добавляем id
        email_part = email_part[:20]
        tag = f"{email_part}_{user_id}"
        return tag.lower()

    async def create(self, *, email: str, password_hash: str, display_name: str, tag: str, avatar_url: str | None) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            tag=tag,
            avatar_url=avatar_url,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_tag(self, user: User, new_tag: str) -> User:
        """Обновить тег пользователя"""
        user.tag = new_tag.lower()
        await self.session.flush()
        return user
