from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.core import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_token(*, subject: str | None, expires_delta: timedelta, secret_key: str) -> str:
    now = datetime.now(tz=timezone.utc)
    expire = now + expires_delta
    payload: dict[str, Any] = {"exp": int(expire.timestamp()), "iat": int(now.timestamp())}
    if subject is not None:
        payload["sub"] = subject
    return jwt.encode(payload, secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str | None) -> str:
    return create_token(
        subject=subject,
        expires_delta=timedelta(minutes=settings.access_token_expires_minutes),
        secret_key=settings.jwt_secret_key,
    )


def create_refresh_token(subject: str | None) -> str:
    return create_token(
        subject=subject,
        expires_delta=timedelta(minutes=settings.refresh_token_expires_minutes),
        secret_key=settings.jwt_refresh_secret_key,
    )
