# Отладка ошибки 500 при загрузке медиа

## Проблема
```
POST http://localhost:8000/api/v1/attachments/confirm
[HTTP/1.1 500 Internal Server Error]
```

## Шаги для диагностики

### 1. Проверить что backend запущен с логами

```bash
# Остановить текущий backend если запущен
# Ctrl+C

# Запустить с детальными логами
uvicorn app.main:app --reload --log-level debug
```

### 2. Попробовать загрузить файл снова

Откройте frontend и попробуйте загрузить "дуду.jpg" еще раз.

### 3. Смотреть логи backend

В терминале где запущен uvicorn вы должны увидеть:

**✅ Успешная загрузка:**
```
INFO: Confirming upload for attachment_id: abc-123-def
INFO: User: 1, filename: дуду.jpg, size: 150000
INFO: Storage key: attachments/abc-123-def/дуду.jpg
INFO: Attachment record created in DB
INFO: Transaction committed
INFO: Download URL generated: http://localhost:9000/attachments...
INFO: 127.0.0.1:57234 - "POST /api/v1/attachments/confirm HTTP/1.1" 201
```

**❌ Ошибка - будет показана причина:**
```
ERROR: Error confirming attachment: ...
```

## Частые причины ошибок

### 1. MinIO не запущен

**Симптом:**
```
ERROR: Error confirming attachment: Could not connect to the endpoint URL
```

**Решение:**
```bash
docker-compose up -d minio
```

### 2. Таблица attachments не создана

**Симптом:**
```
ERROR: relation "attachments" does not exist
```

**Решение:**
```bash
alembic upgrade head
```

### 3. Файл не был загружен в MinIO

**Симптом:**
```
ERROR: The specified key does not exist
```

**Причина:** Файл не был успешно загружен через presigned URL.

**Проверка:**
1. Откройте MinIO Console: http://localhost:9001
2. Логин: minioadmin / minioadmin
3. Перейдите в bucket "attachments"
4. Проверьте есть ли там папки с UUID

### 4. Неправильный формат данных

**Симптом:**
```
ERROR: Field required
```

**Проверка:** Убедитесь что frontend отправляет все поля:
```typescript
{
  attachment_id: string,
  filename: string,
  content_type: string,
  size_bytes: number,
  metadata?: object
}
```

### 5. Проблемы с session/commit

**Симптом:**
```
ERROR: This Connection is closed
```

**Решение:** Перезапустить backend

## Тест вручную через curl

### 1. Получить токен
```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}' \
  | jq -r '.tokens.access_token')
```

### 2. Получить presigned URL
```bash
curl -X POST http://localhost:8000/api/v1/attachments/presigned \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{"filename":"test.jpg","content_type":"image/jpeg"}'
```

Сохраните `attachment_id` из ответа.

### 3. Загрузить файл в MinIO

Используйте presigned URL и fields из предыдущего ответа.

### 4. Подтвердить загрузку
```bash
curl -X POST http://localhost:8000/api/v1/attachments/confirm \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "attachment_id": "ваш-uuid-тут",
    "filename": "test.jpg",
    "content_type": "image/jpeg",
    "size_bytes": 1024,
    "metadata": {"width": 100, "height": 100}
  }'
```

## Что проверить

### ✅ MinIO работает
```bash
curl http://localhost:9000/minio/health/live
# Должен вернуть XML
```

### ✅ PostgreSQL работает
```bash
docker ps | grep nodus_postgres
# Должен показать running
```

### ✅ Backend запущен
```bash
curl http://localhost:8000/health
# Или любой другой endpoint
```

### ✅ Таблица существует
```bash
alembic current
# Должен показать: 7a428b8e8dac (head)
```

### ✅ Bucket создан
```bash
docker exec nodus_minio mc ls /data/
# Должен показать: attachments/
```

## Решение после диагностики

После того как вы увидели реальную ошибку в логах backend:

1. **Ошибка связи с MinIO** → Проверить docker-compose, перезапустить MinIO
2. **Ошибка БД** → Проверить миграции, подключение к PostgreSQL
3. **Ошибка валидации** → Проверить что frontend отправляет правильные данные
4. **Другая ошибка** → Скопировать полный stack trace и проанализировать

## Успешный результат

После исправления вы должны увидеть:

**Backend logs:**
```
INFO: Confirming upload for attachment_id: ...
INFO: Attachment record created in DB
INFO: Transaction committed
INFO: 127.0.0.1:xxxx - "POST /api/v1/attachments/confirm HTTP/1.1" 201
```

**Frontend:**
- Прогресс-бар загрузки завершается
- Изображение появляется в сообщении
- Нет ошибок в console

## Дополнительная помощь

Если проблема не решается:

1. Скопируйте полный stack trace из backend логов
2. Проверьте версии зависимостей: `pip list | grep boto3`
3. Проверьте .env файл на корректность настроек MinIO
