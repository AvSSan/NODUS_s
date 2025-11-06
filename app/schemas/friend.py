from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserRead


class FriendRequest(BaseModel):
    """Запрос на добавление в друзья"""
    friend_id: int


class FriendshipRead(BaseModel):
    """Информация о дружбе"""
    id: int
    user_id: int
    friend_id: int
    status: str  # pending, accepted, blocked
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class FriendWithUser(BaseModel):
    """Запрос в друзья с информацией о пользователе"""
    friendship: FriendshipRead
    user: UserRead


class FriendStatusUpdate(BaseModel):
    """Обновление статуса дружбы"""
    status: str  # accepted, blocked
