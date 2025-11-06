# Быстрый старт медиа-системы

## ✅ Миграция успешно применена!

Таблица `attachments` создана в базе данных.

## Следующие шаги

### 1. Запустить MinIO (если еще не запущен)

**Вариант A: Docker (рекомендуется)**

Создайте `docker-compose.yml` в корне проекта:

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

volumes:
  minio_data:
```

Запустить:
```bash
docker-compose up -d minio
```

**Вариант B: Локальная установка**

Скачайте и запустите MinIO:
- Windows: https://dl.min.io/server/minio/release/windows-amd64/minio.exe
- Запустить: `minio.exe server C:\minio\data --console-address ":9001"`

### 2. Проверить настройки в .env

```env
# PostgreSQL (должен быть уже настроен)
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/nodus

# MinIO (добавить, если нет)
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=attachments
```

### 3. Установить зависимости (если не установлены)

```bash
pip install -e .
```

Это установит:
- `boto3` - для работы с MinIO
- `python-multipart` - для загрузки файлов

### 4. Запустить backend

```bash
uvicorn app.main:app --reload
```

Backend будет доступен на: http://localhost:8000

При первом запросе к `/attachments/presigned` автоматически создастся bucket `attachments` в MinIO.

### 5. Протестировать API

```bash
# Получить токен (если нужен)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Получить presigned URL
curl -X POST http://localhost:8000/api/v1/attachments/presigned \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{"filename":"test.jpg","content_type":"image/jpeg"}'
```

## 📊 Что готово

### Backend
- ✅ Таблица `attachments` в БД
- ✅ MinIO клиент (`app/core/storage.py`)
- ✅ AttachmentService (`app/services/attachments.py`)
- ✅ Repository (`app/repositories/attachment.py`)
- ✅ API endpoints (`app/api/v1/attachments.py`):
  - POST `/api/v1/attachments/presigned`
  - POST `/api/v1/attachments/confirm`
  - GET `/api/v1/attachments/{id}`

### Frontend
- ✅ AttachmentService (`src/services/attachment.service.ts`)
- ✅ MediaAttachment компонент
- ✅ MediaUploadPreview компонент
- ✅ MessageInputBarWithMedia компонент
- ✅ Расширенные типы в `types.ts`

## 🎯 Использование на Frontend

### 1. Импортировать новые компоненты

```tsx
import { MessageInputBarWithMedia } from '@/components/MessageInputBarWithMedia';
import { MediaAttachment } from '@/components/MediaAttachment';
```

### 2. Заменить MessageInputBar

```tsx
// Было:
<MessageInputBar
  onSubmit={handleSendMessage}
  // ...
/>

// Стало:
<MessageInputBarWithMedia
  onSubmit={async (text, replyToId, attachments) => {
    // attachments - массив AttachmentResponse
    await handleSendMessageWithMedia(text, replyToId, attachments);
  }}
  onTypingChange={handleTypingChange}
  replyingTo={replyingTo}
  onCancelReply={() => setReplyingTo(null)}
/>
```

### 3. Обработать attachments в handleSendMessage

```tsx
const handleSendMessageWithMedia = async (
  text: string,
  replyToId?: number,
  attachments?: AttachmentResponse[]
) => {
  if (attachments && attachments.length > 0) {
    for (const attachment of attachments) {
      const mediaType = attachmentService.getMediaType(attachment.content_type);
      
      await messageService.createMessage({
        chat_id: chatId,
        type: mediaType === 'image' ? 'image' : 
              mediaType === 'video' ? 'video' : 'file',
        content: text || null,
        payload: {
          attachment_id: attachment.id,
          filename: attachment.filename,
          ...attachment.metadata,
        },
        reply_to_id: replyToId,
      });
    }
  } else if (text.trim()) {
    // Обычное текстовое сообщение
    await messageService.createMessage({
      chat_id: chatId,
      type: 'text',
      content: text,
      reply_to_id: replyToId,
    });
  }
};
```

### 4. Отобразить медиа в ChatBubble

```tsx
// В компоненте ChatBubble
{message.type === 'image' && message.payload && (
  <MediaAttachment
    attachment={{
      id: message.payload.attachment_id,
      filename: message.payload.filename || 'image',
      content_type: 'image/jpeg',
      size_bytes: 0,
      url: `${API_URL}/attachments/${message.payload.attachment_id}`, // Или получить через API
      metadata: message.payload,
      created_at: message.ts,
    }}
  />
)}

{message.type === 'video' && message.payload && (
  <MediaAttachment
    attachment={{
      id: message.payload.attachment_id,
      filename: message.payload.filename || 'video',
      content_type: 'video/mp4',
      // ... аналогично изображению
    }}
  />
)}
```

## 🔧 Troubleshooting

### Backend не запускается

**Ошибка: "No module named 'boto3'"**
```bash
pip install boto3
```

**Ошибка: "Cannot connect to MinIO"**
- Проверьте что MinIO запущен: `docker ps | grep minio`
- Проверьте URL в .env: `S3_ENDPOINT_URL=http://localhost:9000`

### Frontend ошибки

**TypeScript ошибки в компонентах**
- Убедитесь что `types.ts` обновлен
- Перезапустите TypeScript server в VS Code

**404 на /attachments/presigned**
- Проверьте что backend запущен
- Проверьте что роутер зарегистрирован в `app/api/router.py`

## 📚 Документация

Полная документация:
- **Backend Setup**: `MEDIA_SETUP.md`
- **Usage Guide**: `MEDIA_GUIDE.md` (в NODUS_f)

## 🎉 Готово!

Система полностью настроена и готова к использованию.

Теперь можно:
- ✅ Загружать изображения
- ✅ Загружать видео
- ✅ Загружать аудио
- ✅ Загружать файлы
- ✅ Отслеживать прогресс загрузки
- ✅ Просматривать превью перед отправкой
- ✅ Отображать медиа в сообщениях

Приятного использования! 🚀
