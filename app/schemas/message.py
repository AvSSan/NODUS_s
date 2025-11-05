from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    chat_id: int
    type: str
    content: str | None = None
    payload: dict | None = None
    reply_to_id: int | None = None  # ID сообщения, на которое отвечаем


class MessageUpdate(BaseModel):
    content: str | None = None
    payload: dict | None = None


class MessageRead(BaseModel):
    id: int
    chat_id: int
    author_id: int | None
    type: str
    content: str | None
    payload: dict | None
    status: str  # delivered, read
    ts: datetime
    reply_to_id: int | None = None
    is_deleted: bool = False
    deleted_at: datetime | None = None
    updated_at: datetime | None = None
    reactions: list["ReactionRead"] = []

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    """Ответ с пагинацией для списка сообщений"""
    messages: list[MessageRead]
    has_more: bool
    next_cursor: int | None = None  # ID следующего сообщения для пагинации


class ReactionCreate(BaseModel):
    """Создание реакции на сообщение"""
    emoji: str = Field(..., min_length=1, max_length=10)


class ReactionRead(BaseModel):
    """Реакция на сообщение"""
    id: int
    message_id: int
    user_id: int
    emoji: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TypingIndicator(BaseModel):
    """Индикатор набора текста"""
    chat_id: int
    is_typing: bool
