from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserRead


class ChatMemberRead(BaseModel):
    id: int
    user: UserRead
    role: str
    joined_at: datetime

    model_config = {"from_attributes": True}


class ChatCreate(BaseModel):
    title: str
    is_group: bool = True
    member_ids: list[int]


class ChatUpdate(BaseModel):
    title: str | None = None


class ChatRead(BaseModel):
    id: int
    title: str
    is_group: bool
    created_at: datetime

    model_config = {"from_attributes": True}
