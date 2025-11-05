from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt

from app.core import jwt
from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль против хеша"""
    password_bytes = plain_password.encode('utf-8')
    # bcrypt автоматически обрезает до 72 байт, но лучше сделать явно
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """Создает bcrypt хеш пароля"""
    password_bytes = password.encode('utf-8')
    # bcrypt ограничен 72 байтами
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


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
