from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.storage import get_minio_client
from app.schemas.attachment import PresignedRequest, PresignedResponse


class AttachmentService:
    """Сервис для работы с вложениями"""

    def __init__(self):
        self.minio = get_minio_client()

    def create_presigned_post(self, request: PresignedRequest) -> PresignedResponse:
        """
        Создает presigned POST URL для загрузки файла
        
        Args:
            request: Запрос с именем файла и content_type
            
        Returns:
            Presigned URL и поля для формы загрузки
        """
        attachment_id = str(uuid4())
        expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=10)
        
        # Формируем путь к файлу в MinIO
        # Структура: attachments/{attachment_id}/{filename}
        storage_key = f"attachments/{attachment_id}/{request.filename}"
        
        # Получаем presigned POST данные от MinIO
        presigned_data = self.minio.generate_presigned_post(
            key=storage_key,
            content_type=request.content_type,
            max_size_mb=100,  # Максимум 100 МБ
            expires_in=600,  # 10 минут
        )
        
        return PresignedResponse(
            attachment_id=attachment_id,
            url=presigned_data['url'],
            fields=presigned_data['fields'],
            expires_at=expires_at,
        )

    def get_download_url(self, attachment_id: str, filename: str, expires_in: int = 3600) -> str:
        """
        Генерирует presigned URL для скачивания файла
        
        Args:
            attachment_id: ID вложения
            filename: Имя файла
            expires_in: Время жизни URL в секундах
            
        Returns:
            Presigned URL для скачивания
        """
        storage_key = f"attachments/{attachment_id}/{filename}"
        return self.minio.generate_presigned_url(storage_key, expires_in=expires_in)

    def delete_attachment(self, attachment_id: str, filename: str) -> None:
        """Удаляет файл из хранилища"""
        storage_key = f"attachments/{attachment_id}/{filename}"
        self.minio.delete_file(storage_key)
