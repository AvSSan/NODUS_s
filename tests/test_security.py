from __future__ import annotations

from datetime import timedelta

import pytest

pytest.importorskip("pydantic")
pytest.importorskip("pydantic_settings")

from app.core import jwt
from app.core.config import settings
from app.core.security import create_token, get_password_hash, verify_password


def test_password_hash_roundtrip() -> None:
    password = "secret123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)


def test_token_contains_subject() -> None:
    token = create_token(subject="42", expires_delta=timedelta(minutes=5), secret_key=settings.jwt_secret_key)
    decoded = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert decoded["sub"] == "42"
