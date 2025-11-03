from __future__ import annotations

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

    async def create(self, *, email: str, password_hash: str, display_name: str, avatar_url: str | None) -> User:
        user = User(email=email, password_hash=password_hash, display_name=display_name, avatar_url=avatar_url)
        self.session.add(user)
        await self.session.flush()
        return user
