# Настройка медиа-системы (Backend)

## Быстрый старт

### 1. Установка зависимостей

```bash
# Из корня NODUS_s
pip install -e .
```

Это установит:
- `boto3>=1.34.0` - для работы с MinIO/S3
- `python-multipart>=0.0.9` - для обработки multipart/form-data

### 2. Настройка MinIO

#### Через Docker (рекомендуется)

Создайте `docker-compose.yml` или добавьте в существующий:

```yaml
version: '3.8'

services:
  minio:
    image: minio/minio:latest
    container_name: nodus_minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

volumes:
  minio_data:
```

Запуск:
```bash
docker-compose up -d minio
```

MinIO Console доступен по адресу: http://localhost:9001

#### Ручная установка

1. Скачайте MinIO: https://min.io/download
2. Запустите:
```bash
minio server /data --console-address ":9001"
```

### 3. Переменные окружения

В `.env` файле:

```env
# Существующие настройки...

# MinIO Configuration
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=attachments
```

Для production используйте безопасные credentials:
```env
S3_ACCESS_KEY=your_secure_access_key
S3_SECRET_KEY=your_secure_secret_key
```

### 4. Применение миграций

```bash
# Применить миграцию для создания таблицы attachments
alembic upgrade head
```

Это создаст таблицу:
```sql
CREATE TABLE attachments (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    size_bytes INTEGER NOT NULL,
    storage_key VARCHAR(512) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 5. Проверка работоспособности

```bash
# Запустить сервер
uvicorn app.main:app --reload

# В другом терминале проверить endpoints
curl http://localhost:8000/api/v1/attachments/presigned \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.jpg", "content_type": "image/jpeg"}'
```

## Архитектура

### Компоненты

1. **MinIOClient** (`app/core/storage.py`)
   - Singleton клиент для работы с MinIO
   - Автоматическое создание bucket
   - Генерация presigned URLs

2. **AttachmentService** (`app/services/attachments.py`)
   - Бизнес-логика работы с вложениями
   - Создание presigned POST URLs
   - Генерация download URLs

3. **AttachmentRepository** (`app/repositories/attachment.py`)
   - CRUD операции с БД
   - Связь вложений с сообщениями

4. **API Endpoints** (`app/api/v1/attachments.py`)
   - POST `/attachments/presigned` - получение presigned URL
   - POST `/attachments/confirm` - подтверждение загрузки
   - GET `/attachments/{id}` - получение информации

### Процесс загрузки

```
Frontend                Backend               MinIO
   |                       |                    |
   |--POST /presigned----->|                    |
   |                       |                    |
   |<--presigned data------|                    |
   |                       |                    |
   |----------POST file------------------>|     |
   |                       |                    |
   |<--200 OK--------------------------|        |
   |                       |                    |
   |--POST /confirm------->|                    |
   |                       |                    |
   |                    [Save to DB]            |
   |                       |                    |
   |<--attachment info-----|                    |
```

## Конфигурация MinIO

### Bucket Policy (публичное чтение)

Backend автоматически устанавливает policy при создании bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "*"},
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::attachments/*"]
    }
  ]
}
```

### CORS Configuration

Для работы с frontend добавьте CORS через MinIO Console:

```json
[
  {
    "AllowedOrigins": ["http://localhost:5173"],
    "AllowedMethods": ["GET", "POST", "PUT"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"]
  }
]
```

### Limits

В `app/services/attachments.py` настройте лимиты:

```python
presigned_data = self.minio.generate_presigned_post(
    key=storage_key,
    content_type=request.content_type,
    max_size_mb=100,  # Максимальный размер файла
    expires_in=600,   # Время жизни presigned URL (секунды)
)
```

## Production Deployment

### 1. Используйте внешний MinIO

```env
S3_ENDPOINT_URL=https://minio.yourcompany.com
S3_ACCESS_KEY=production_access_key
S3_SECRET_KEY=production_secret_key
S3_BUCKET=prod-attachments
```

### 2. Настройте CDN (опционально)

```python
# В app/core/config.py
cdn_url: str = "https://cdn.yourcompany.com"

# В app/services/attachments.py
def get_download_url(self, attachment_id: str, filename: str) -> str:
    if settings.cdn_url:
        return f"{settings.cdn_url}/attachments/{attachment_id}/{filename}"
    return self.minio.generate_presigned_url(...)
```

### 3. Настройте retention policy

Для автоматического удаления старых файлов:

```bash
mc ilm add minio/attachments --expiry-days 365
```

### 4. Мониторинг

Добавьте логирование в `AttachmentService`:

```python
import logging

logger = logging.getLogger(__name__)

async def uploadFile(...):
    logger.info(f"Upload started: {filename}, size: {size_bytes}")
    try:
        # ... upload logic
        logger.info(f"Upload completed: {attachment_id}")
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise
```

## Безопасность

### 1. Валидация файлов

Добавьте валидацию типов файлов:

```python
ALLOWED_CONTENT_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'video/mp4', 'video/webm',
    'audio/mpeg', 'audio/ogg', 'audio/opus',
    'application/pdf',
}

def create_presigned_post(self, request: PresignedRequest):
    if request.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(f"Content type {request.content_type} not allowed")
    # ...
```

### 2. Rate Limiting

Используйте slowapi для ограничения запросов:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/presigned")
@limiter.limit("10/minute")
async def create_presigned_url(...):
    # ...
```

### 3. Virus Scanning

Интегрируйте ClamAV для проверки файлов:

```python
import pyclamd

def scan_file(file_path: str) -> bool:
    cd = pyclamd.ClamdUnixSocket()
    result = cd.scan_file(file_path)
    return result is None  # None = clean
```

## Troubleshooting

### MinIO connection refused

```bash
# Проверить что MinIO запущен
docker ps | grep minio

# Проверить логи
docker logs nodus_minio

# Перезапустить
docker-compose restart minio
```

### Bucket not found

```python
# Backend создаст bucket автоматически при первом запуске
# Если ошибка сохраняется, создайте вручную:
from app.core.storage import get_minio_client
client = get_minio_client()
# Bucket создастся в __init__
```

### Presigned URL expired

Увеличьте время жизни в `app/services/attachments.py`:

```python
expires_in=1800,  # 30 минут вместо 10
```

### CORS errors

1. Проверьте CORS policy в MinIO Console
2. Убедитесь что `AllowedOrigins` включает ваш frontend URL
3. Проверьте что MinIO доступен по тому же протоколу (http/https)

## Maintenance

### Очистка неиспользуемых файлов

Создайте периодическую задачу:

```python
# app/workers/cleanup.py
async def cleanup_orphaned_attachments():
    """Удаляет файлы без связанных сообщений старше 7 дней"""
    cutoff = datetime.now() - timedelta(days=7)
    orphaned = await db.query(Attachment).filter(
        Attachment.message_id.is_(None),
        Attachment.created_at < cutoff
    ).all()
    
    for attachment in orphaned:
        minio.delete_file(attachment.storage_key)
        await db.delete(attachment)
```

### Backup

```bash
# Создать snapshot MinIO bucket
mc mirror minio/attachments /backup/attachments-$(date +%Y%m%d)

# Или используйте MinIO backup
mc admin service restart minio
```

## Мониторинг

### Метрики для Prometheus

```python
from prometheus_client import Counter, Histogram

upload_counter = Counter('attachments_uploads_total', 'Total uploads')
upload_size = Histogram('attachments_upload_size_bytes', 'Upload size')

async def uploadFile(...):
    upload_counter.inc()
    upload_size.observe(size_bytes)
    # ...
```

### Health Check

```python
@router.get("/health")
async def health_check():
    try:
        # Проверить MinIO
        minio = get_minio_client()
        minio.s3_client.head_bucket(Bucket=settings.s3_bucket)
        return {"status": "ok", "minio": "connected"}
    except Exception as e:
        return {"status": "error", "minio": str(e)}
```

## Следующие шаги

1. ✅ Установить зависимости
2. ✅ Настроить MinIO
3. ✅ Применить миграции
4. ✅ Проверить endpoints
5. 🔄 Настроить CORS для production
6. 🔄 Добавить валидацию файлов
7. 🔄 Настроить мониторинг
8. 🔄 Создать backup стратегию
