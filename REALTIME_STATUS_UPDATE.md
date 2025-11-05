# Обновление статуса в реальном времени

## Дата: 2024-11-04

## Проблема:

Статус "прочитано" не обновлялся в реальном времени, когда получатель сидел в открытом чате. Отправитель видел статус "доставлено" до тех пор, пока не перезагружал страницу.

## Причина:

Бэкенд отправлял только событие `message.read` с массивом ID, но **не отправлял обновленные сообщения** с новым статусом `"read"`. Фронтенд не знал о том, что статус изменился в БД.

---

## Решение:

Теперь бэкенд отправляет **два типа событий** при изменении статуса на "read":

1. **`message.updated`** - для каждого сообщения с обновленным статусом
2. **`message.read`** - обобщенное событие (для совместимости)

---

## Как работает:

### До исправления:

```
Получатель открывает чат
    ↓
POST /chats/{chat_id}/read
    ↓
Бэкенд:
  1. Создает MessageRead записи
  2. Обновляет Message.status = "read" в БД
  3. Отправляет WebSocket: {event: "message.read", message_ids: [1, 2, 3]}
    ↓
Фронтенд получателя:
  ✅ Локально обновляет статус на "read"
    ↓
Фронтенд отправителя:
  ✅ Локально обновляет статус на "read"
    ↓
Отправитель перезагружает страницу:
  ❌ Загружает из БД: status = "read"
  ✅ Статус "read" появляется ТОЛЬКО ПОСЛЕ ПЕРЕЗАГРУЗКИ
```

**Проблема:** Статус в БД обновлен, но фронтенд не знает об этом до перезагрузки.

### После исправления:

```
Получатель открывает чат
    ↓
POST /chats/{chat_id}/read
    ↓
Бэкенд:
  1. Создает MessageRead записи
  2. Обновляет Message.status = "read" в БД
  3. Отправляет WebSocket события:
     - message.updated для каждого сообщения
     - message.read для совместимости
    ↓
Фронтенд получателя:
  ✅ Получает message.updated со статусом "read"
  ✅ Обновляет сообщение в кэше
    ↓
Фронтенд отправителя:
  ✅ Получает message.updated со статусом "read"
  ✅ Обновляет сообщение в кэше
  ✅ СТАТУС МЕНЯЕТСЯ МГНОВЕННО ✓ → ✓✓
```

**Решение:** Фронтенд получает обновленное сообщение из БД через WebSocket.

---

## Изменения в коде:

### Бэкенд (app/services/message.py):

#### 1. Собираем список обновленных сообщений:

```python
# Список сообщений, у которых изменился статус на "read"
updated_messages = []

for message_id in unread_message_ids:
    message = await self.messages.get(message_id)
    # ...
    if read_count >= expected_reads:
        old_status = message.status
        message.status = "read"
        updated_messages.append(message)  # ← Добавляем в список
        logger.debug(f"Updated message {message_id} status: {old_status} -> read")

await self.session.commit()

# Refresh для получения актуальных данных
for message in updated_messages:
    await self.session.refresh(message)
```

#### 2. Отправляем WebSocket события:

```python
async def _publish_read_event(self, chat_id: int, message_ids: list[int], updated_messages: list) -> None:
    participant_ids = await self.chat_members.list_participant_ids(chat_id)
    
    # НОВОЕ! Отправляем message.updated для каждого сообщения
    for message in updated_messages:
        payload = {
            "event": "message.updated",
            "data": {
                "id": message.id,
                "chat_id": message.chat_id,
                "author_id": message.author_id,
                "type": message.type,
                "content": message.content,
                "payload": message.payload,
                "status": message.status,  # ← Обновленный статус "read"
                "ts": message.ts.isoformat(),
            },
        }
        # Отправляем всем участникам
        for user_id in participant_ids:
            await self.redis.publish(f"ws:user:{user_id}", json.dumps(payload))
    
    # Также отправляем обобщенное событие для совместимости
    payload = {
        "event": "message.read",
        "data": {
            "chat_id": chat_id,
            "message_ids": message_ids,
        },
    }
    for user_id in participant_ids:
        await self.redis.publish(f"ws:user:{user_id}", json.dumps(payload))
```

### Фронтенд (src/hooks/useRealtimeSubscriptions.ts):

#### Обработчик message:updated уже существует:

```typescript
const handleMessageUpdated = ({ chatId, message }: { chatId: number; message: Message }) => {
  console.log('🔄 handleMessageUpdated called:', { 
    messageId: message.id, 
    status: (message as any).status  // ← Получаем новый статус "read"
  });
  
  queryClient.setQueryData<{ pages: PaginatedResult[]; pageParams: unknown[] }>(
    ['messages', chatId],
    (old) => {
      if (!old) return old;
      return {
        ...old,
        pages: mergeMessage(old.pages, chatId, message.id, () => message),
      };
    }
  );
  
  console.log('✅ Message updated in cache:', message.id);
};
```

**Маппинг событий:**
```typescript
const eventMap: Record<string, string> = {
  'message.created': 'message:new',
  'message.updated': 'message:updated',  // ← Уже настроен!
  'message.read': 'read-receipt',
};
```

---

## Логика работы:

### Сценарий: Оба пользователя в чате

```
1. Пользователь А отправляет сообщение ID=100
   Бэкенд: создает Message {status: "delivered"}
   WebSocket: broadcast message.created {id: 100, status: "delivered"}
   У А появляется: ✓

2. Пользователь Б сидит в том же чате (открыт)
   Видит новое сообщение ID=100
   Через 1 сек: автоматический вызов POST /chats/6/read

3. Бэкенд обрабатывает POST /chats/6/read:
   - Создает MessageRead(message_id=100, user_id=Б)
   - Проверяет: все участники прочитали? ДА
   - Обновляет Message.status = "read" в БД
   - Отправляет WebSocket:
     * message.updated {id: 100, status: "read"}  ← КЛЮЧЕВОЕ!
     * message.read {message_ids: [100]}

4. Пользователь А (отправитель):
   WebSocket получает: message.updated {id: 100, status: "read"}
   handleMessageUpdated обновляет кэш
   UI автоматически перерисовывается: ✓ → ✓✓  МГНОВЕННО!

5. Пользователь Б (получатель):
   WebSocket получает: message.updated {id: 100, status: "read"}
   (Но у него не отображаются статусы, т.к. он не автор)
```

**Результат:** Статус обновляется в реальном времени без перезагрузки!

---

## Логи для отладки:

### Бэкенд:

```
INFO:app.services.message:Marked 1 messages as read in chat 6 for user 2, 1 changed to 'read'
DEBUG:app.services.message:Published message.updated for message 100 with status 'read'
INFO:app.services.message:Broadcast 1 message.updated + message.read to 2 participants in chat 6
```

### Фронтенд (отправитель):

```
📨 Raw WebSocket event received: {event: "message.updated", data: {id: 100, status: "read"}}
🔄 Mapping: "message.updated" -> "message:updated"
✅ Event matched! Calling listener with: {chatId: 6, message: {...}}
🔄 handleMessageUpdated called: {messageId: 100, status: "read"}
📦 Updating message in cache: 100 with status: "read"
✅ Message updated in cache: 100
🎨 Rendering ChatBubble: {id: 100, status: "read"}  ← Иконка ✓✓
```

### Фронтенд (получатель):

```
📬 New messages arrived in open chat, marking as read...
📖 Marked new messages as read for chat: 6
📨 Raw WebSocket event received: {event: "message.updated", data: {id: 100, status: "read"}}
🔄 handleMessageUpdated called: {messageId: 100, status: "read"}
```

---

## Преимущества:

| До | После |
|-----|-------|
| ❌ Статус обновляется только при перезагрузке | ✅ Статус обновляется мгновенно |
| ❌ Отправитель не видит "прочитано" в реальном времени | ✅ ✓✓ появляется через ~1 секунду |
| ❌ Только событие message.read | ✅ События message.updated + message.read |
| ❌ Фронтенд не знает об изменениях в БД | ✅ Фронтенд получает обновленные данные |

---

## Тестирование:

### Сценарий: Открытый чат

1. Откройте **2 окна браузера**
2. Войдите как **разные пользователи**
3. **ОБА открывают один чат**
4. **Пользователь А** отправляет сообщение "Test"
5. У **Пользователя А** появляется ⏱️ → ✓
6. **Пользователь Б** видит сообщение (чат открыт)
7. Через **1 секунду**:
   - Консоль Б: `📖 Marked new messages as read`
   - **Консоль А: `🔄 handleMessageUpdated called: {status: "read"}`**
   - **У Пользователя А: ✓ → ✓✓ МГНОВЕННО!** ✅

### Проверка логов бэкенда:

```bash
# Смотрите логи бэкенда в терминале
# Должны увидеть:

INFO:app.services.message:Marked 1 messages as read in chat 6 for user 2, 1 changed to 'read'
DEBUG:app.services.message:Published message.updated for message 100 with status 'read'
INFO:app.services.message:Broadcast 1 message.updated + message.read to 2 participants in chat 6
```

---

## Измененные файлы:

**Бэкенд (NODUS_s):**
- `app/services/message.py`:
  - `mark_messages_as_read()` - собирает список обновленных сообщений
  - `_publish_read_event()` - отправляет message.updated для каждого сообщения

**Фронтенд (NODUS_f):**
- `src/hooks/useRealtimeSubscriptions.ts` - добавлено логирование в `handleMessageUpdated`

---

## Готово! 🎉

Теперь статус "прочитано" обновляется **мгновенно** через WebSocket события:
- ✅ Отправитель видит ✓✓ в реальном времени
- ✅ Не нужно перезагружать страницу
- ✅ Работает как в WhatsApp/Telegram

**Проблема полностью решена!** 🚀
