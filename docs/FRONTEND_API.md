# API Документация для Frontend

## 🔗 Base URL
```
http://localhost:8000/api/v1
```

## 🔐 Аутентификация

Все защищенные endpoints требуют JWT токен в заголовке:
```
Authorization: Bearer <access_token>
```

### Типы токенов
- **Access Token**: живет 15 минут, используется для API запросов
- **Refresh Token**: живет 7 дней, используется для обновления access token

---

## 📋 Endpoints

### 1. Аутентификация (`/auth`)

#### POST `/auth/register`
Регистрация нового пользователя

**Headers:**
```
Content-Type: application/json
Idempotency-Key: <unique-uuid>
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "display_name": "John Doe",
  "avatar_url": "https://example.com/avatar.jpg" // опционально
}
```

**Response 201:**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "display_name": "John Doe",
    "avatar_url": "https://example.com/avatar.jpg",
    "created_at": "2024-03-26T10:00:00"
  },
  "tokens": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "expires_in": 900.0
  }
}
```

**Errors:**
- `400` - Email уже зарегистрирован
- `409` - Дублирующийся запрос (Idempotency-Key уже использован)

---

#### POST `/auth/login`
Вход в систему

**Headers:**
```
Content-Type: application/json
Idempotency-Key: <unique-uuid>
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response 200:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 900.0
}
```

**Errors:**
- `401` - Неверные учетные данные

---

#### POST `/auth/refresh`
Обновление access токена

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response 200:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 900.0
}
```

---

### 2. Пользователи (`/users`)

#### GET `/users/me`
Получить информацию о текущем пользователе

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response 200:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "display_name": "John Doe",
  "avatar_url": "https://example.com/avatar.jpg",
  "created_at": "2024-03-26T10:00:00"
}
```

---

### 3. Чаты (`/chats`)

#### GET `/chats`
Получить список чатов пользователя

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response 200:**
```json
[
  {
    "id": 1,
    "title": "General Chat",
    "is_group": true,
    "created_at": "2024-03-26T10:00:00"
  },
  {
    "id": 2,
    "title": "John Doe",
    "is_group": false,
    "created_at": "2024-03-26T11:00:00"
  }
]
```

---

#### POST `/chats`
Создать новый чат

**Headers:**
```
Authorization: Bearer <access_token>
Idempotency-Key: <unique-uuid>
```

**Request Body:**
```json
{
  "title": "New Project Discussion",
  "is_group": true,
  "member_ids": [2, 3, 4]
}
```

**Response 201:**
```json
{
  "id": 3,
  "title": "New Project Discussion",
  "is_group": true,
  "created_at": "2024-03-26T12:00:00"
}
```

**Примечания:**
- Текущий пользователь автоматически добавляется в чат
- Для личного чата (`is_group: false`) укажите только одного пользователя в `member_ids`

---

#### GET `/chats/{chat_id}`
Получить информацию о конкретном чате

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response 200:**
```json
{
  "id": 1,
  "title": "General Chat",
  "is_group": true,
  "created_at": "2024-03-26T10:00:00"
}
```

**Errors:**
- `404` - Чат не найден
- `403` - Пользователь не является участником чата

---

#### PATCH `/chats/{chat_id}`
Обновить информацию о чате

**Headers:**
```
Authorization: Bearer <access_token>
Idempotency-Key: <unique-uuid>
```

**Request Body:**
```json
{
  "title": "Updated Chat Title"
}
```

**Response 200:**
```json
{
  "id": 1,
  "title": "Updated Chat Title",
  "is_group": true,
  "created_at": "2024-03-26T10:00:00"
}
```

---

#### DELETE `/chats/{chat_id}`
Удалить чат

**Headers:**
```
Authorization: Bearer <access_token>
Idempotency-Key: <unique-uuid>
```

**Response 204:** No Content

---

### 4. Сообщения (`/messages`)

#### GET `/messages?chat_id={chat_id}`
Получить сообщения чата

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `chat_id` (required) - ID чата

**Response 200:**
```json
[
  {
    "id": 1,
    "chat_id": 1,
    "author_id": 2,
    "type": "text",
    "content": "Hello everyone!",
    "payload": null,
    "ts": "2024-03-26T12:00:00"
  },
  {
    "id": 2,
    "chat_id": 1,
    "author_id": 1,
    "type": "voice",
    "content": null,
    "payload": {
      "attachment_id": "uuid-here",
      "duration_ms": 5000,
      "codec": "opus",
      "waveform": [10, 20, 30, 40, 50]
    },
    "ts": "2024-03-26T12:01:00"
  }
]
```

**Примечания:**
- Сообщения отсортированы по времени (новые первыми)
- Лимит: 50 сообщений
- Для пагинации используйте параметр `before_id` (в будущем)

---

#### POST `/messages`
Отправить сообщение

**Headers:**
```
Authorization: Bearer <access_token>
Idempotency-Key: <unique-uuid>
```

**Request Body (text):**
```json
{
  "chat_id": 1,
  "type": "text",
  "content": "Hello everyone!"
}
```

**Request Body (voice):**
```json
{
  "chat_id": 1,
  "type": "voice",
  "content": null,
  "payload": {
    "attachment_id": "uuid-from-attachments-api",
    "duration_ms": 5000,
    "codec": "opus",
    "waveform": [10, 20, 30, 40, 50]
  }
}
```

**Response 201:**
```json
{
  "id": 3,
  "chat_id": 1,
  "author_id": 1,
  "type": "text",
  "content": "Hello everyone!",
  "payload": null,
  "ts": "2024-03-26T12:05:00"
}
```

**Типы сообщений:**
- `text` - текстовое сообщение (требуется `content`)
- `voice` - голосовое сообщение (требуется `payload` с полями: `attachment_id`, `duration_ms`, `codec`)
- `system` - системное сообщение

**Errors:**
- `400` - Невалидные данные (например, отсутствующие поля для voice)
- `403` - Пользователь не является участником чата

---

#### PATCH `/messages/{message_id}`
Обновить сообщение

**Headers:**
```
Authorization: Bearer <access_token>
Idempotency-Key: <unique-uuid>
```

**Request Body:**
```json
{
  "content": "Updated message text",
  "payload": null
}
```

**Response 200:**
```json
{
  "id": 3,
  "chat_id": 1,
  "author_id": 1,
  "type": "text",
  "content": "Updated message text",
  "payload": null,
  "ts": "2024-03-26T12:05:00"
}
```

**Errors:**
- `404` - Сообщение не найдено
- `403` - Можно редактировать только свои сообщения

---

### 5. Вложения (`/attachments`)

#### POST `/attachments`
Получить pre-signed URL для загрузки файла

**Headers:**
```
Authorization: Bearer <access_token>
Idempotency-Key: <unique-uuid>
```

**Request Body:**
```json
{
  "filename": "audio.opus",
  "content_type": "audio/opus"
}
```

**Response 200:**
```json
{
  "attachment_id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "http://localhost:9000/attachments",
  "fields": {
    "key": "550e8400-e29b-41d4-a716-446655440000/audio.opus",
    "Content-Type": "audio/opus",
    "X-Amz-Signature": "signature-here"
  },
  "expires_at": "2024-03-26T12:15:00"
}
```

**Как использовать:**
1. Получите pre-signed URL от этого endpoint
2. Используйте `multipart/form-data` POST запрос к `url` с полями из `fields` + файл
3. Используйте `attachment_id` при отправке сообщения типа `voice`

**Пример загрузки файла (JavaScript):**
```javascript
const formData = new FormData();
formData.append('key', response.fields.key);
formData.append('Content-Type', response.fields['Content-Type']);
formData.append('X-Amz-Signature', response.fields['X-Amz-Signature']);
formData.append('file', audioBlob);

await fetch(response.url, {
  method: 'POST',
  body: formData
});
```

---

## 🔌 WebSocket

### Подключение
```
ws://localhost:8000/ws
```

### Формат событий

**Message Created:**
```json
{
  "event": "message.created",
  "data": {
    "id": 3,
    "chat_id": 1,
    "author_id": 2,
    "type": "text",
    "content": "New message",
    "payload": null,
    "ts": "2024-03-26T12:10:00"
  }
}
```

**Message Updated:**
```json
{
  "event": "message.updated",
  "data": {
    "id": 3,
    "chat_id": 1,
    "author_id": 2,
    "type": "text",
    "content": "Updated message",
    "payload": null,
    "ts": "2024-03-26T12:10:00"
  }
}
```

**Пример подключения (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.event, 'Data:', data.data);
  
  // Обработка события
  if (data.event === 'message.created') {
    // Добавить новое сообщение в UI
  } else if (data.event === 'message.updated') {
    // Обновить сообщение в UI
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket closed');
  // Реконнект логика
};
```

---

## 🔑 Idempotency

Для POST, PATCH, DELETE операций требуется заголовок `Idempotency-Key`.

**Что такое Idempotency Key:**
- Уникальный UUID для каждого запроса
- Предотвращает дублирование операций при повторных запросах
- Хранится 24 часа после успешного выполнения

**Пример генерации (JavaScript):**
```javascript
function generateIdempotencyKey() {
  return crypto.randomUUID();
}

// Использование
const key = generateIdempotencyKey();
fetch('/api/v1/chats', {
  method: 'POST',
  headers: {
    'Idempotency-Key': key,
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({...})
});
```

**Ошибки:**
- `400` - Отсутствует заголовок `Idempotency-Key`
- `409` - Запрос с таким ключом уже выполняется или был выполнен

---

## ⚠️ Обработка ошибок

### Стандартный формат ошибки
```json
{
  "detail": "Error message here"
}
```

### HTTP коды
- `200` - Успешный запрос
- `201` - Ресурс создан
- `204` - Успешно, без контента
- `400` - Ошибка валидации
- `401` - Не авторизован / невалидный токен
- `403` - Доступ запрещен
- `404` - Ресурс не найден
- `409` - Конфликт (дублирующийся запрос)
- `500` - Внутренняя ошибка сервера

---

## 📱 Рекомендации по интеграции

### 1. Управление токенами
```javascript
class AuthService {
  constructor() {
    this.accessToken = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
  }

  async refreshAccessToken() {
    const response = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: this.refreshToken })
    });
    
    if (response.ok) {
      const data = await response.json();
      this.accessToken = data.access_token;
      this.refreshToken = data.refresh_token;
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
    } else {
      // Перенаправить на страницу входа
      this.logout();
    }
  }

  async apiRequest(url, options = {}) {
    let response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${this.accessToken}`
      }
    });

    // Если токен истек, обновить и повторить
    if (response.status === 401) {
      await this.refreshAccessToken();
      response = await fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          'Authorization': `Bearer ${this.accessToken}`
        }
      });
    }

    return response;
  }
}
```

### 2. WebSocket реконнект
```javascript
class WebSocketManager {
  constructor(url) {
    this.url = url;
    this.reconnectDelay = 1000;
    this.maxReconnectDelay = 30000;
    this.connect();
  }

  connect() {
    this.ws = new WebSocket(this.url);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectDelay = 1000;
    };

    this.ws.onclose = () => {
      console.log('WebSocket closed, reconnecting...');
      setTimeout(() => {
        this.reconnectDelay = Math.min(
          this.reconnectDelay * 2,
          this.maxReconnectDelay
        );
        this.connect();
      }, this.reconnectDelay);
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
  }

  handleMessage(data) {
    // Обработка событий
  }
}
```

### 3. Кэширование и оптимистичные обновления
- Кэшируйте список чатов и сообщений
- Используйте оптимистичные обновления для лучшего UX
- Синхронизируйте с WebSocket событиями

---

## 🎯 Типичные сценарии

### Сценарий 1: Регистрация и вход
```javascript
// 1. Регистрация
const registerResponse = await fetch('/api/v1/auth/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Idempotency-Key': crypto.randomUUID()
  },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123',
    display_name: 'John Doe'
  })
});

const { user, tokens } = await registerResponse.json();

// 2. Сохранить токены
localStorage.setItem('access_token', tokens.access_token);
localStorage.setItem('refresh_token', tokens.refresh_token);

// 3. Получить профиль
const meResponse = await fetch('/api/v1/users/me', {
  headers: {
    'Authorization': `Bearer ${tokens.access_token}`
  }
});
```

### Сценарий 2: Создание чата и отправка сообщения
```javascript
// 1. Создать чат
const chatResponse = await fetch('/api/v1/chats', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Idempotency-Key': crypto.randomUUID(),
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: 'New Chat',
    is_group: true,
    member_ids: [2, 3]
  })
});

const chat = await chatResponse.json();

// 2. Отправить сообщение
const messageResponse = await fetch('/api/v1/messages', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Idempotency-Key': crypto.randomUUID(),
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    chat_id: chat.id,
    type: 'text',
    content: 'Hello everyone!'
  })
});
```

### Сценарий 3: Загрузка и отправка аудио
```javascript
// 1. Получить pre-signed URL
const presignedResponse = await fetch('/api/v1/attachments', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Idempotency-Key': crypto.randomUUID(),
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    filename: 'voice.opus',
    content_type: 'audio/opus'
  })
});

const presigned = await presignedResponse.json();

// 2. Загрузить файл в S3
const formData = new FormData();
formData.append('key', presigned.fields.key);
formData.append('Content-Type', presigned.fields['Content-Type']);
formData.append('X-Amz-Signature', presigned.fields['X-Amz-Signature']);
formData.append('file', audioBlob);

await fetch(presigned.url, {
  method: 'POST',
  body: formData
});

// 3. Отправить сообщение с вложением
await fetch('/api/v1/messages', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Idempotency-Key': crypto.randomUUID(),
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    chat_id: chatId,
    type: 'voice',
    payload: {
      attachment_id: presigned.attachment_id,
      duration_ms: 5000,
      codec: 'opus',
      waveform: [10, 20, 30, 40, 50]
    }
  })
});
```

---

## 📞 Поддержка

При возникновении вопросов или проблем:
1. Проверьте интерактивную документацию: http://localhost:8000/docs
2. Обратитесь к backend команде
3. Создайте issue в репозитории

---

**Версия документации:** 1.0.0  
**Последнее обновление:** 2024-03-26
