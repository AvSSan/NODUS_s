# 🔧 Backend Fix - Проблема #2: Удаление чата не синхронизируется

**Дата:** 2025-11-05  
**Статус:** ✅ ИСПРАВЛЕНО  
**Ответственный:** Backend Team

---

## 📋 Описание проблемы

**Проблема #2 из REALTIME_SYNC_FIXES.md:**
> Когда пользователь А удаляет чат с пользователем Б, у пользователя Б чат не удаляется, пока не перезагрузит страницу.

---

## 🔍 Анализ причины

### Что было:
Backend **НЕ отправлял** WebSocket событие `chat.deleted` при удалении чата.

**Код ДО исправления:**
```python
# app/services/chat.py
async def delete_chat(self, chat: Chat) -> None:
    await self.session.delete(chat)
    await self.session.commit()
    # ❌ Никакого WebSocket события
```

### Почему это проблема:
- Пользователь А удаляет чат через API: `DELETE /api/v1/chats/{chat_id}`
- Backend удаляет чат из базы данных
- Пользователь Б **не получает уведомление** через WebSocket
- У пользователя Б чат остается в списке до перезагрузки страницы

---

## ✅ Решение

### Изменения в Backend:

#### 1. Обновлен `ChatService` для отправки WebSocket событий

**Файл:** `app/services/chat.py`

```python
from __future__ import annotations

import json
import logging

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Chat
from app.repositories.chat import ChatMemberRepository, ChatRepository
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, session: AsyncSession, redis: Redis | None = None):
        self.session = session
        self.redis = redis  # ✅ Добавлен Redis
        self.chats = ChatRepository(session)
        self.members = ChatMemberRepository(session)
        self.users = UserRepository(session)

    async def delete_chat(self, chat: Chat, deleted_by: int) -> None:
        """Удалить чат и отправить WebSocket событие всем участникам"""
        chat_id = chat.id
        
        # Получаем список участников ДО удаления чата
        participant_ids = await self.members.list_participant_ids(chat_id)
        
        # Удаляем чат
        await self.session.delete(chat)
        await self.session.commit()
        
        # ✅ Отправляем WebSocket событие всем участникам
        if self.redis:
            await self._publish_chat_deleted_event(chat_id, deleted_by, participant_ids)
        else:
            logger.warning(f"Redis not available, chat.deleted event not sent for chat {chat_id}")

    async def _publish_chat_deleted_event(
        self, chat_id: int, deleted_by: int, participant_ids: list[int]
    ) -> None:
        """Отправить WebSocket событие chat.deleted всем участникам чата"""
        payload = {
            "event": "chat.deleted",
            "data": {
                "id": chat_id,
                "deleted_by": deleted_by,
            },
        }
        payload_json = json.dumps(payload)
        
        # Отправляем событие в персональный канал каждого участника
        for user_id in participant_ids:
            channel = f"ws:user:{user_id}"
            await self.redis.publish(channel, payload_json)
            logger.debug(f"Published chat.deleted to user {user_id} for chat {chat_id}")
        
        logger.info(f"Broadcast chat.deleted to {len(participant_ids)} participants for chat {chat_id}")
```

#### 2. Обновлен API endpoint

**Файл:** `app/api/v1/chats.py`

```python
@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: int,
    current_user: int = Depends(get_current_user),
    idempotency: tuple[str, IdempotencyService] = Depends(require_idempotency),
    session: AsyncSession = Depends(get_session),
    redis = Depends(get_redis),  # ✅ Добавлен Redis
) -> None:
    key, service = idempotency
    chat = await get_chat_or_404(chat_id, session)
    member_repo = ChatMemberRepository(session)
    member = await member_repo.get_member(chat_id=chat_id, user_id=current_user)
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    chat_service = ChatService(session, redis)  # ✅ Передаем Redis
    await chat_service.delete_chat(chat, deleted_by=current_user)  # ✅ Передаем deleted_by
    await service.mark_completed(key)
```

---

## 📡 WebSocket Event Format

### `chat.deleted`

**Формат события:**
```json
{
  "event": "chat.deleted",
  "data": {
    "id": 6,
    "deleted_by": 3
  }
}
```

**Поля:**
- `id` (number) - ID удаленного чата
- `deleted_by` (number) - ID пользователя, который удалил чат

**Когда отправляется:**
- При вызове `DELETE /api/v1/chats/{chat_id}`
- Отправляется **всем участникам чата** одновременно через их персональные WebSocket каналы

---

## 🎯 Что нужно фронтенду

### 1. Добавить обработчик WebSocket события

```typescript
// src/hooks/useRealtimeSubscriptions.ts

const handleChatDeleted = ({ id }: { id: number }) => {
  // Удаляем чат из списка чатов
  queryClient.setQueryData<Chat[]>(['chats'], (old) => {
    if (!old) return old;
    return old.filter((chat) => chat.id !== id);
  });
  
  // Опционально: показать уведомление
  toast.info('Чат был удален');
  
  // Опционально: если мы находимся в удаленном чате - перенаправить
  if (currentChatId === id) {
    navigate('/chats');
  }
};

// Подписка на событие
apiAdapter.on('chat:deleted', handleChatDeleted);
```

### 2. Тестирование

**Сценарий тестирования:**
1. Откройте два браузера с разными пользователями (А и Б)
2. Создайте чат между пользователями А и Б
3. Пользователь А удаляет чат
4. **Ожидаемый результат:** У пользователя Б чат моментально исчезает из списка без перезагрузки

---

## 📝 Обновленная документация

Документация `FRONTEND_INTEGRATION_GUIDE.md` была обновлена:
- ✅ Добавлено описание события `chat.deleted` в секции WebSocket событий
- ✅ Добавлен пример обработчика в `useRealtimeSubscriptions`
- ✅ Добавлены примеры Frontend кода для интеграции

---

## 🔧 Измененные файлы

| Файл | Изменения |
|------|-----------|
| `app/services/chat.py` | ✅ Добавлен параметр `redis`, добавлен метод `_publish_chat_deleted_event`, обновлен `delete_chat` |
| `app/api/v1/chats.py` | ✅ Добавлен `redis` dependency, передается `deleted_by` в `delete_chat` |
| `FRONTEND_INTEGRATION_GUIDE.md` | ✅ Добавлено описание события `chat.deleted` и примеры |

---

## 🧪 Проверка работоспособности

### Backend logs:
```
INFO: Broadcast chat.deleted to 2 participants for chat 6
DEBUG: Published chat.deleted to user 3 for chat 6
DEBUG: Published chat.deleted to user 5 for chat 6
```

### WebSocket message (в консоли браузера):
```json
{
  "event": "chat.deleted",
  "data": {
    "id": 6,
    "deleted_by": 3
  }
}
```

---

## 📊 Итоговая таблица проблем

| # | Проблема | Статус | Ответственный |
|---|----------|--------|---------------|
| 1 | Реакции не отображаются в реальном времени | ✅ Исправлено | Frontend |
| 2 | Удаление чата не синхронизируется | ✅ Исправлено | **Backend** |
| 3 | Реакции пропадают при редактировании | ✅ Исправлено | Frontend |

---

## ✅ Статус

**Проблема #2 полностью решена на стороне Backend.**

Frontend может теперь:
1. Получать событие `chat.deleted` через WebSocket
2. Удалять чат из UI в реальном времени
3. Показывать уведомления пользователю

**Следующий шаг:** Frontend team должна добавить обработчик события `chat:deleted` в `useRealtimeSubscriptions`.

---

**Автор:** Backend Team  
**Дата:** 2025-11-05  
**Версия:** Backend v2.1
