from __future__ import annotations

from datetime import timedelta
from typing import AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import jwt
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_session
from app.repositories.user import UserRepository
from app.schemas.auth import TokenPair
from app.services.idempotency import IdempotencyService


async def get_redis() -> AsyncGenerator[Redis, None]:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield redis
    finally:
        await redis.aclose()


async def get_idempotency_service(redis: Redis = Depends(get_redis)) -> IdempotencyService:
    return IdempotencyService(redis)


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    authorization: str = Header(None, alias="Authorization"),
) -> int:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = authorization.split()[1]
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    repo = UserRepository(session)
    user = await repo.get(int(subject))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user.id


async def refresh_tokens(refresh_token: str) -> TokenPair:
    try:
        payload = jwt.decode(
            refresh_token,
            settings.jwt_refresh_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    return TokenPair(
        access_token=create_access_token(subject=subject),
        refresh_token=refresh_token,
        expires_in=timedelta(minutes=settings.access_token_expires_minutes).total_seconds(),
    )
