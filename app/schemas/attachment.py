from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PresignedRequest(BaseModel):
    filename: str
    content_type: str


class PresignedResponse(BaseModel):
    attachment_id: str
    url: str
    fields: dict[str, str]
    expires_at: datetime
