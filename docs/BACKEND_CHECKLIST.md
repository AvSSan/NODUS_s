# 🔍 Чеклист для бэкенд команды

## Проблемы фронтенда, которые могут быть вызваны бэкендом

### ❌ Проблема 1: Сообщения не появляются без перезагрузки
### ❌ Проблема 2: При перезагрузке страницы перенаправляет на логин

---

## ✅ Что проверить на бэкенде

### 1. CORS настроен правильно

**Файл:** Ваш основной файл приложения (например `app/main.py`)

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Для разработки
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Проверка:**
```bash
# Должен вернуть заголовок Access-Control-Allow-Origin
curl -I http://localhost:8000/api/v1/chats \
  -H "Origin: http://localhost:5173"
```

---

### 2. WebSocket endpoint работает с токеном в query параметре

**Ожидаемое поведение:**
- Фронтенд подключается: `ws://localhost:8000/ws?token=<access_token>`
- Бэкенд должен извлечь токен из query string
- Валидировать токен
- Установить соединение

**Пример на FastAPI:**
```python
from fastapi import WebSocket, Query, Depends

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),  # Токен из query параметра
):
    # Валидация токена
    user = await validate_token(token)
    if not user:
        await websocket.close(code=1008)  # Policy Violation
        return
    
    await websocket.accept()
    # ... остальная логика
```

**Проверка через браузер:**
1. Откройте http://localhost:8000/docs
2. Зарегистрируйтесь и получите access_token
3. Откройте Console в DevTools
4. Выполните:
```javascript
const token = "YOUR_ACCESS_TOKEN";
const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);
ws.onopen = () => console.log('✅ Connected');
ws.onerror = (e) => console.error('❌ Error:', e);
ws.onmessage = (e) => console.log('📨 Message:', e.data);
```

---

### 3. WebSocket отправляет события ВСЕМ участникам чата

**Критическая ошибка:** Отправка события только отправителю сообщения

**Правильное поведение:**
1. Пользователь A отправляет сообщение в чат
2. Бэкенд сохраняет в БД
3. Бэкенд находит ВСЕХ участников чата
4. Отправляет WebSocket событие КАЖДОМУ участнику, кто онлайн

**Пример:**
```python
# ❌ НЕПРАВИЛЬНО - только отправителю
await websocket.send_json({
    "event": "message.created",
    "data": message_dict
})

# ✅ ПРАВИЛЬНО - всем участникам чата
chat = await get_chat(message.chat_id)
for participant in chat.participants:
    if participant.id in active_websocket_connections:
        ws = active_websocket_connections[participant.id]
        await ws.send_json({
            "event": "message.created",
            "data": message_dict
        })
```

---

### 4. Формат WebSocket событий

**Фронтенд ожидает:**
```json
{
  "event": "message.created",
  "data": {
    "id": 123,
    "chat_id": 456,
    "author_id": 789,
    "type": "text",
    "content": "Hello World!",
    "payload": null,
    "ts": "2024-11-04T14:30:00Z"
  }
}
```

**Важно:**
- ✅ Корневой объект содержит `event` и `data`
- ✅ `event` это строка: `"message.created"` или `"message.updated"`
- ✅ `data` это полный объект сообщения
- ❌ НЕ отправляйте просто объект сообщения без обертки

---

### 5. API /chats возвращает participants

**Endpoint:** `GET /api/v1/chats` и `GET /api/v1/chats/{id}`

**Обязательно включите поле `participants`:**
```json
{
  "id": 1,
  "title": "Chat Title",
  "is_group": false,
  "created_at": "2024-11-04T12:00:00Z",
  "participants": [
    {
      "id": 1,
      "email": "user1@example.com",
      "display_name": "Alice",
      "tag": "alice",
      "avatar_url": null,
      "created_at": "2024-11-04T10:00:00Z"
    },
    {
      "id": 2,
      "email": "user2@example.com",
      "display_name": "Bob",
      "tag": "bob",
      "avatar_url": null,
      "created_at": "2024-11-04T11:00:00Z"
    }
  ]
}
```

**Почему это важно:**
- Для личных чатов фронтенд показывает имя собеседника (не title)
- В сообщениях показывается имя отправителя
- Без participants фронтенд не может корректно работать

**Pydantic модель должна включать:**
```python
from pydantic import BaseModel
from typing import List

class UserRead(BaseModel):
    id: int
    email: str
    display_name: str
    tag: str
    avatar_url: str | None
    created_at: datetime

class ChatRead(BaseModel):
    id: int
    title: str
    is_group: bool
    created_at: datetime
    participants: List[UserRead]  # ОБЯЗАТЕЛЬНО!
```

---

### 6. Токены живут достаточно долго

**Проверьте настройки:**
```python
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Минимум 15 минут
REFRESH_TOKEN_EXPIRE_DAYS = 7     # Минимум 7 дней
```

**Проблема:** Если access_token живет меньше 1 минуты, пользователь постоянно разлогинивается.

---

### 7. GET /users/me работает правильно

**Проверка:**
```bash
# Получите токен через /auth/login
TOKEN="your_access_token"

# Запрос должен вернуть данные пользователя, а не 401
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN"
```

**Ожидаемый ответ:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "display_name": "John Doe",
  "tag": "johndoe",
  "avatar_url": null,
  "created_at": "2024-11-04T10:00:00Z"
}
```

**Если возвращает 401:**
- Проверьте JWT валидацию
- Проверьте формат заголовка `Authorization: Bearer <token>`
- Проверьте, что токен не истек

---

### 8. POST /chats/direct работает правильно

**Endpoint должен:**
1. Принимать `{"user_id": 123}`
2. Проверять, что чат между текущим пользователем и `user_id` не существует
3. Если существует - вернуть существующий чат (статус 200)
4. Если не существует - создать новый чат (статус 200)
5. Вернуть чат с полем `participants`

**Пример запроса:**
```bash
curl -X POST http://localhost:8000/api/v1/chats/direct \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"user_id": 2}'
```

**Ожидаемый ответ:**
```json
{
  "id": 5,
  "title": "Direct Message",
  "is_group": false,
  "created_at": "2024-11-04T14:00:00Z",
  "participants": [
    {"id": 1, "display_name": "Alice", ...},
    {"id": 2, "display_name": "Bob", ...}
  ]
}
```

---

### 9. GET /users/search?tag=username работает

**Проверка:**
```bash
curl "http://localhost:8000/api/v1/users/search?tag=alice" \
  -H "Authorization: Bearer $TOKEN"
```

**Ожидаемый ответ:**
```json
{
  "id": 1,
  "email": "alice@example.com",
  "display_name": "Alice",
  "tag": "alice",
  "avatar_url": null,
  "created_at": "2024-11-04T10:00:00Z"
}
```

**Должен работать:**
- С символом @: `?tag=@alice`
- Без символа @: `?tag=alice`

---

## 🧪 Тестовый сценарий для проверки

### Шаг 1: Создать двух пользователей

```bash
# Пользователь 1
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "email": "alice@test.com",
    "password": "password123",
    "display_name": "Alice"
  }'
# Сохраните access_token как TOKEN1

# Пользователь 2
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "email": "bob@test.com",
    "password": "password123",
    "display_name": "Bob"
  }'
# Сохраните access_token как TOKEN2
```

### Шаг 2: Создать личный чат

```bash
# Alice создает чат с Bob (user_id=2)
curl -X POST http://localhost:8000/api/v1/chats/direct \
  -H "Authorization: Bearer $TOKEN1" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"user_id": 2}'
# Сохраните chat_id
```

### Шаг 3: Подключить WebSocket для обоих

**Терминал 1 (Alice):**
```bash
# Используйте wscat или браузер
wscat -c "ws://localhost:8000/ws?token=$TOKEN1"
```

**Терминал 2 (Bob):**
```bash
wscat -c "ws://localhost:8000/ws?token=$TOKEN2"
```

### Шаг 4: Отправить сообщение

```bash
# Alice отправляет сообщение
curl -X POST http://localhost:8000/api/v1/messages \
  -H "Authorization: Bearer $TOKEN1" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "chat_id": 1,
    "type": "text",
    "content": "Hello Bob!"
  }'
```

### Шаг 5: Проверить результат

**✅ Ожидаемое поведение:**
- В терминале Alice появляется событие WebSocket
- В терминале Bob **ТОЖЕ** появляется событие WebSocket
- Оба получают одинаковое событие:
  ```json
  {
    "event": "message.created",
    "data": {
      "id": 1,
      "chat_id": 1,
      "author_id": 1,
      "type": "text",
      "content": "Hello Bob!",
      "payload": null,
      "ts": "2024-11-04T14:30:00Z"
    }
  }
  ```

**❌ Если Bob не получил событие - ПРОБЛЕМА в бэкенде!**

---

## 🐛 Логи для отладки

Добавьте логи в критические места:

```python
import logging

logger = logging.getLogger(__name__)

# При подключении WebSocket
logger.info(f"WebSocket connected: user_id={user.id}")

# При отправке сообщения
logger.info(f"Message created: {message.id} in chat {message.chat_id}")

# При отправке WebSocket события
logger.info(f"Sending WebSocket event to user {user_id}: {event_type}")

# При отправке события всем участникам
logger.info(f"Broadcasting to {len(participants)} participants")
```

---

## 📝 Итоговый чеклист

- [ ] CORS настроен на `allow_origins=["*"]`
- [ ] WebSocket принимает токен в query: `?token=...`
- [ ] WebSocket отправляет события ВСЕМ участникам чата
- [ ] Формат событий: `{"event": "...", "data": {...}}`
- [ ] API возвращает `participants` в чатах
- [ ] GET /users/me работает с токеном
- [ ] POST /chats/direct создает/возвращает DM
- [ ] GET /users/search?tag=... работает
- [ ] Токены живут минимум 15 минут
- [ ] Проведен тестовый сценарий с двумя пользователями

---

## 📞 Обратная связь

После проверки отправьте фронтенд команде:
- ✅ Что работает
- ❌ Что не работает
- 📋 Логи ошибок (если есть)

---

**Версия:** 1.0.0  
**Дата:** 2024-11-04
