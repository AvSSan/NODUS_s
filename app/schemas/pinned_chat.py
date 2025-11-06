from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.chat import ChatRead


class PinChatRequest(BaseModel):
    """Запрос на закрепление чата"""
    chat_id: int


class PinnedChatRead(BaseModel):
    """Информация о закрепленном чате"""
    id: int
    user_id: int
    chat_id: int
    pin_order: int
    pinned_at: datetime

    model_config = {"from_attributes": True}


class PinnedChatsResponse(BaseModel):
    """Список закрепленных чатов"""
    chats: list[ChatRead]
    total: int
    max_pins: int
