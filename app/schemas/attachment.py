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


class AttachmentMetadata(BaseModel):
    """Метаданные для различных типов вложений"""
    # Для аудио
    duration_ms: int | None = None
    codec: str | None = None
    waveform: list[int] | None = None
    
    # Для изображений
    width: int | None = None
    height: int | None = None
    
    # Для видео
    video_codec: str | None = None
    audio_codec: str | None = None
    fps: float | None = None
    bitrate: int | None = None


class AttachmentCreate(BaseModel):
    """Схема для создания вложения после загрузки"""
    attachment_id: str
    filename: str
    content_type: str
    size_bytes: int
    metadata: dict | None = None


class AttachmentResponse(BaseModel):
    """Схема ответа с информацией о вложении"""
    id: str
    filename: str
    content_type: str
    size_bytes: int
    url: str  # Presigned URL для скачивания
    metadata: dict | None = None
    created_at: datetime

    class Config:
        from_attributes = True
