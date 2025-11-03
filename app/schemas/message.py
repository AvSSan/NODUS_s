from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MessageCreate(BaseModel):
    chat_id: int
    type: str
    content: str | None = None
    payload: dict | None = None


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
    ts: datetime

    model_config = {"from_attributes": True}
