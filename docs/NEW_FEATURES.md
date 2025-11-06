# Новые функции

## 1. Система друзей

### Описание
Пользователи могут добавлять друг друга в друзья. Система работает через запросы: один пользователь отправляет запрос, другой принимает или блокирует его.

### Статусы дружбы
- `pending` - запрос отправлен, ожидает ответа
- `accepted` - запрос принят, пользователи являются друзьями
- `blocked` - запрос заблокирован

### API Endpoints

#### POST `/v1/friends`
Отправить запрос на добавление в друзья.

**Request Body:**
```json
{
  "friend_id": 2
}
```

**Response:** `201 Created`
```json
{
  "message": "Friend request sent"
}
```

#### GET `/v1/friends`
Получить список друзей (только со статусом `accepted`).

**Response:** `200 OK`
```json
[
  {
    "id": 2,
    "email": "friend@example.com",
    "display_name": "Friend Name",
    "tag": "friend123",
    "avatar_url": null,
    "created_at": "2024-11-06T08:00:00"
  }
]
```

#### GET `/v1/friends/requests/incoming`
Получить список входящих запросов в друзья.

**Response:** `200 OK`
```json
[
  {
    "friendship": {
      "id": 1,
      "user_id": 2,
      "friend_id": 1,
      "status": "pending",
      "created_at": "2024-11-06T08:00:00",
      "updated_at": null
    },
    "user": {
      "id": 2,
      "email": "sender@example.com",
      "display_name": "Sender Name",
      "tag": "sender123",
      "avatar_url": null,
      "created_at": "2024-11-06T08:00:00"
    }
  }
]
```

#### GET `/v1/friends/requests/outgoing`
Получить список исходящих запросов в друзья.

**Response:** `200 OK` (формат аналогичен incoming)

#### PATCH `/v1/friends/{friend_id}`
Принять или заблокировать запрос в друзья (только для получателя запроса).

**Request Body:**
```json
{
  "status": "accepted"  // или "blocked"
}
```

**Response:** `200 OK`
```json
{
  "message": "Friend request accepted"
}
```

#### DELETE `/v1/friends/{friend_id}`
Удалить из друзей или отменить запрос.

**Response:** `204 No Content`

---

## 2. Закрепление чатов

### Описание
Пользователи могут закреплять до 5 чатов, которые будут отображаться в начале списка. Чаты имеют порядок закрепления.

### Ограничения
- Максимум 5 закрепленных чатов на пользователя
- Автоматическая переупорядочивание при откреплении

### API Endpoints

#### POST `/v1/pinned-chats`
Закрепить чат.

**Request Body:**
```json
{
  "chat_id": 1
}
```

**Response:** `201 Created`
```json
{
  "message": "Chat pinned successfully"
}
```

**Errors:**
- `400 Bad Request` - если достигнут лимит закрепленных чатов
- `400 Bad Request` - если чат уже закреплен
- `403 Forbidden` - если пользователь не является участником чата

#### GET `/v1/pinned-chats`
Получить список закрепленных чатов.

**Response:** `200 OK`
```json
{
  "chats": [
    {
      "id": 1,
      "title": "Important Chat",
      "is_group": true,
      "created_at": "2024-11-06T08:00:00",
      "participants": [...]
    }
  ],
  "total": 1,
  "max_pins": 5
}
```

#### DELETE `/v1/pinned-chats/{chat_id}`
Открепить чат.

**Response:** `204 No Content`

---

## 3. Поиск сообщений в чате

### Описание
Полнотекстовый поиск сообщений в конкретном чате. Поиск регистронезависимый, поддерживает пагинацию.

### API Endpoint

#### GET `/v1/messages/search`
Поиск сообщений в чате.

**Query Parameters:**
- `chat_id` (required) - ID чата для поиска
- `query` (required) - Поисковый запрос (минимум 1 символ)
- `limit` (optional, default=50) - Максимальное количество результатов
- `offset` (optional, default=0) - Смещение для пагинации

**Example Request:**
```
GET /v1/messages/search?chat_id=1&query=hello&limit=20&offset=0
```

**Response:** `200 OK`
```json
[
  {
    "id": 123,
    "chat_id": 1,
    "author_id": 2,
    "type": "text",
    "content": "Hello, how are you?",
    "payload": null,
    "status": "delivered",
    "ts": "2024-11-06T08:00:00",
    "reply_to_id": null,
    "is_deleted": false,
    "deleted_at": null,
    "updated_at": null,
    "reactions": []
  }
]
```

**Errors:**
- `400 Bad Request` - если поисковый запрос пустой
- `403 Forbidden` - если пользователь не является участником чата

---

## Миграция базы данных

Для применения изменений в базе данных выполните:

```bash
alembic upgrade head
```

Создана новая миграция `20241106_0006_add_friends_and_pinned_chats.py` которая добавляет:
- Таблицу `friends` для хранения дружеских связей
- Таблицу `pinned_chats` для закрепленных чатов
- Соответствующие индексы и ограничения

## Модели данных

### Friend
```python
class Friend(Base):
    id: int
    user_id: int          # Пользователь, отправивший запрос
    friend_id: int        # Пользователь, получивший запрос
    status: str           # pending, accepted, blocked
    created_at: datetime
    updated_at: datetime | None
```

### PinnedChat
```python
class PinnedChat(Base):
    id: int
    user_id: int
    chat_id: int
    pin_order: int        # Порядок закрепления (0, 1, 2, ...)
    pinned_at: datetime
```

## Примеры использования

### Добавление в друзья
```python
# 1. Пользователь A отправляет запрос пользователю B
POST /v1/friends
{"friend_id": 2}

# 2. Пользователь B видит входящий запрос
GET /v1/friends/requests/incoming

# 3. Пользователь B принимает запрос
PATCH /v1/friends/1
{"status": "accepted"}

# 4. Теперь оба могут видеть друг друга в списке друзей
GET /v1/friends
```

### Закрепление чата
```python
# 1. Закрепить чат
POST /v1/pinned-chats
{"chat_id": 1}

# 2. Просмотреть закрепленные чаты
GET /v1/pinned-chats

# 3. Открепить чат
DELETE /v1/pinned-chats/1
```

### Поиск сообщений
```python
# Найти все сообщения со словом "meeting" в чате 1
GET /v1/messages/search?chat_id=1&query=meeting

# Поиск с пагинацией
GET /v1/messages/search?chat_id=1&query=hello&limit=10&offset=0
GET /v1/messages/search?chat_id=1&query=hello&limit=10&offset=10
```
