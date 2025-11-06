from __future__ import annotations

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from functools import lru_cache

from app.core.config import settings


class MinIOClient:
    """MinIO клиент для работы с объектным хранилищем"""

    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1',  # MinIO требует указания региона
        )
        self.bucket_name = settings.s3_bucket
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Создает bucket если его нет"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == '404':
                # Bucket не существует, создаем
                self.s3_client.create_bucket(Bucket=self.bucket_name)
                # Устанавливаем публичную политику для чтения
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                        }
                    ]
                }
                import json
                self.s3_client.put_bucket_policy(
                    Bucket=self.bucket_name,
                    Policy=json.dumps(policy)
                )
            else:
                raise

    def generate_presigned_post(
        self,
        key: str,
        content_type: str,
        max_size_mb: int = 50,
        expires_in: int = 600,
    ) -> dict[str, object]:
        """
        Генерирует presigned POST URL для загрузки файла
        
        Args:
            key: Путь к файлу в bucket
            content_type: MIME тип файла
            max_size_mb: Максимальный размер файла в МБ
            expires_in: Время жизни URL в секундах
            
        Returns:
            dict с url и fields для формы загрузки
        """
        conditions = [
            {"key": key},
            {"Content-Type": content_type},
            ["content-length-range", 0, max_size_mb * 1024 * 1024],
        ]

        presigned_data = self.s3_client.generate_presigned_post(
            Bucket=self.bucket_name,
            Key=key,
            Fields={"Content-Type": content_type},
            Conditions=conditions,
            ExpiresIn=expires_in,
        )

        return presigned_data

    def generate_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Генерирует presigned URL для скачивания файла
        
        Args:
            key: Путь к файлу в bucket
            expires_in: Время жизни URL в секундах
            
        Returns:
            Presigned URL
        """
        url = self.s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': key,
            },
            ExpiresIn=expires_in,
        )
        return url

    def delete_file(self, key: str) -> None:
        """Удаляет файл из хранилища"""
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)

    def file_exists(self, key: str) -> bool:
        """Проверяет существование файла"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def get_file_metadata(self, key: str) -> dict[str, object]:
        """Получает метаданные файла"""
        response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
        return {
            'content_type': response.get('ContentType'),
            'size': response.get('ContentLength'),
            'last_modified': response.get('LastModified'),
            'metadata': response.get('Metadata', {}),
        }


@lru_cache
def get_minio_client() -> MinIOClient:
    """Возвращает singleton instance MinIO клиента"""
    return MinIOClient()
