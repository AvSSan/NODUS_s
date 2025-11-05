from __future__ import annotations

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import jwt
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.domain.models import User
from app.repositories.user import UserRepository
from app.schemas.auth import TokenPair


class AuthenticationError(Exception):
    pass


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)

    async def register(self, *, email: str, password: str, display_name: str, avatar_url: str | None) -> User:
        existing = await self.users.get_by_email(email)
        if existing is not None:
            raise AuthenticationError("Email already registered")

        password_hash = get_password_hash(password)
        
        # Создаём пользователя с временным тегом
        temp_tag = "temp_" + email.split('@')[0][:20]
        user = await self.users.create(
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            tag=temp_tag,
            avatar_url=avatar_url,
        )
        await self.session.flush()
        
        # Генерируем настоящий тег на основе email и id
        initial_tag = self.users.generate_initial_tag(email, user.id)
        user.tag = initial_tag
        
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def login(self, *, email: str, password: str) -> TokenPair:
        user = await self.users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid credentials")

        return TokenPair(
            access_token=create_access_token(subject=str(user.id)),
            refresh_token=create_refresh_token(subject=str(user.id)),
            expires_in=timedelta(minutes=settings.access_token_expires_minutes).total_seconds(),
        )

    async def refresh(self, *, refresh_token: str) -> TokenPair:
        try:
            payload = jwt.decode(
                refresh_token,
                settings.jwt_refresh_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
        except jwt.JWTError as exc:
            raise AuthenticationError("Invalid refresh token") from exc

        subject = payload.get("sub")
        if subject is None:
            raise AuthenticationError("Invalid refresh token")

        user = await self.users.get(int(subject))
        if user is None:
            raise AuthenticationError("User not found")

        return TokenPair(
            access_token=create_access_token(subject=subject),
            refresh_token=create_refresh_token(subject=subject),
            expires_in=timedelta(minutes=settings.access_token_expires_minutes).total_seconds(),
        )
