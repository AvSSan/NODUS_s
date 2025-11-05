from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UserPresence(BaseModel):
    """Онлайн статус пользователя"""
    user_id: int
    status: str  # online, offline, away
    last_seen: datetime | None = None


class UserPresenceUpdate(BaseModel):
    """Обновление статуса пользователя"""
    status: str  # online, offline, away
