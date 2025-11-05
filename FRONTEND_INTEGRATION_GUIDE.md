# NODUS Backend - Гид по интеграции для Frontend (v2.0)

**Дата:** 2024-11-05  
**Версия API:** v2  
**Backend Версия:** 2.0.0  

---

## 🎉 Что нового в Backend v2.0

Backend был значительно улучшен и теперь поддерживает:

1. ✅ **Пагинация сообщений** (cursor-based)
2. ✅ **Удаление сообщений** (soft delete)
3. ✅ **Реакции на сообщения** (эмодзи)
4. ✅ **Ответы на сообщения** (threads/replies)
5. ✅ **Typing indicators** (индикаторы набора текста)
6. ✅ **Online/Offline status** (статус пользователей)
7. ✅ **Расширенные WebSocket события**

---

## 📊 Новые API Endpoints

### 1. Сообщения - Пагинация

#### `GET /api/v1/messages`

**Изменения:**
- Теперь возвращает объект с пагинацией вместо простого массива
- Добавлены query параметры для cursor-based пагинации

**Request:**
```http
GET /api/v1/messages?chat_id=6&limit=50&before_id=123
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `chat_id` (int, required) - ID чата
- `limit` (int, optional, default: 50) - Количество сообщений
- `before_id` (int, optional) - ID сообщения для пагинации (cursor)

**Response:**
```typescript
interface MessageListResponse {
  messages: Message[];
  has_more: boolean;
  next_cursor: number | null;  // ID для следующей страницы
}

interface Message {
  id: number;
  chat_id: number;
  author_id: number | null;
  type: string;
  content: string | null;
  payload: any | null;
  status: "delivered" | "read";
  ts: string;  // ISO 8601
  
  // НОВЫЕ ПОЛЯ
  reply_to_id: number | null;    // ID сообщения, на которое отвечаем
  is_deleted: boolean;           // Помечено как удаленное
  deleted_at: string | null;     // Когда удалено
  updated_at: string | null;     // Когда отредактировано
  reactions: Reaction[];         // Массив реакций
}
```

**TypeScript Hook Example:**
```typescript
import { useInfiniteQuery } from '@tanstack/react-query';

export function useInfiniteMessages(chatId: number) {
  return useInfiniteQuery({
    queryKey: ['messages', chatId],
    queryFn: async ({ pageParam }) => {
      const params = new URLSearchParams({
        chat_id: chatId.toString(),
        limit: '50',
        ...(pageParam && { before_id: pageParam.toString() }),
      });
      
      const res = await api.get(`/messages?${params}`);
      return res.data; // MessageListResponse
    },
    getNextPageParam: (lastPage) => 
      lastPage.has_more ? lastPage.next_cursor : undefined,
    initialPageParam: undefined,
  });
}
```

---

### 2. Удаление сообщений

#### `DELETE /api/v1/messages/{message_id}`

**Request:**
```http
DELETE /api/v1/messages/123
Authorization: Bearer <access_token>
```

**Response:** `204 No Content`

**Особенности:**
- Это **soft delete** - сообщение помечается как удаленное
- `is_deleted = true`
- `deleted_at` устанавливается в текущее время
- `content` и `payload` очищаются
- WebSocket событие `message.deleted` отправляется всем участникам

**WebSocket Event:**
```json
{
  "event": "message.deleted",
  "data": {
    "id": 123,
    "chat_id": 6,
    "author_id": 3,
    "type": "text",
    "content": null,
    "payload": null,
    "status": "delivered",
    "ts": "2024-11-05T10:00:00Z",
    "reply_to_id": null,
    "is_deleted": true,
    "deleted_at": "2024-11-05T10:05:00Z",
    "updated_at": null
  }
}
```

**Frontend обработка:**
```typescript
// В компоненте сообщения
if (message.is_deleted) {
  return <DeletedMessage />;  // "Сообщение удалено"
}
```

---

### 3. Реакции на сообщения

#### `POST /api/v1/messages/{message_id}/reactions`

Добавить реакцию на сообщение.

**Request:**
```http
POST /api/v1/messages/123/reactions
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "emoji": "👍"
}
```

**Response:** `201 Created`
```json
{
  "id": 45,
  "message_id": 123,
  "user_id": 3,
  "emoji": "👍",
  "created_at": "2024-11-05T10:00:00Z"
}
```

#### `DELETE /api/v1/messages/{message_id}/reactions/{emoji}`

Удалить свою реакцию с сообщения.

**Request:**
```http
DELETE /api/v1/messages/123/reactions/👍
Authorization: Bearer <access_token>
```

**Response:** `204 No Content`

**WebSocket Events:**
```json
{
  "event": "reaction.added",
  "data": {
    "id": 45,
    "message_id": 123,
    "user_id": 3,
    "emoji": "👍",
    "created_at": "2024-11-05T10:00:00Z"
  }
}
```

```json
{
  "event": "reaction.removed",
  "data": {
    "message_id": 123,
    "user_id": 3,
    "emoji": "👍"
  }
}
```

**Frontend Component Example:**
```typescript
// Компонент реакций
function MessageReactions({ message }: { message: Message }) {
  const { mutate: addReaction } = useMutation({
    mutationFn: (emoji: string) => 
      api.post(`/messages/${message.id}/reactions`, { emoji }),
  });
  
  const { mutate: removeReaction } = useMutation({
    mutationFn: (emoji: string) => 
      api.delete(`/messages/${message.id}/reactions/${emoji}`),
  });
  
  // Группируем реакции по emoji
  const groupedReactions = groupBy(message.reactions, 'emoji');
  
  return (
    <div className="flex gap-1">
      {Object.entries(groupedReactions).map(([emoji, reactions]) => (
        <ReactionBubble
          key={emoji}
          emoji={emoji}
          count={reactions.length}
          isActive={reactions.some(r => r.user_id === currentUserId)}
          onClick={() => {
            const hasReaction = reactions.some(r => r.user_id === currentUserId);
            if (hasReaction) {
              removeReaction(emoji);
            } else {
              addReaction(emoji);
            }
          }}
        />
      ))}
      <AddReactionButton onSelect={addReaction} />
    </div>
  );
}
```

---

### 4. Ответы на сообщения (Threads/Replies)

#### `POST /api/v1/messages`

**Изменения:**
- Добавлено поле `reply_to_id` в payload

**Request:**
```http
POST /api/v1/messages
Authorization: Bearer <access_token>
Idempotency-Key: <uuid>
Content-Type: application/json

{
  "chat_id": 6,
  "type": "text",
  "content": "Это ответ на твое сообщение",
  "reply_to_id": 120  // НОВОЕ ПОЛЕ
}
```

**Response:**
```json
{
  "id": 125,
  "chat_id": 6,
  "author_id": 3,
  "type": "text",
  "content": "Это ответ на твое сообщение",
  "payload": null,
  "status": "delivered",
  "ts": "2024-11-05T10:00:00Z",
  "reply_to_id": 120,  // НОВОЕ ПОЛЕ
  "is_deleted": false,
  "deleted_at": null,
  "updated_at": null,
  "reactions": []
}
```

**Frontend Component Example:**
```typescript
function ChatInput({ chatId }: { chatId: number }) {
  const [replyingTo, setReplyingTo] = useState<Message | null>(null);
  
  const { mutate: sendMessage } = useMutation({
    mutationFn: async (content: string) => {
      return api.post('/messages', {
        chat_id: chatId,
        type: 'text',
        content,
        reply_to_id: replyingTo?.id,  // Отправляем reply_to_id
      }, {
        headers: {
          'Idempotency-Key': uuidv4(),
        },
      });
    },
    onSuccess: () => {
      setReplyingTo(null);  // Сбрасываем после отправки
    },
  });
  
  return (
    <div>
      {replyingTo && (
        <ReplyingToBar message={replyingTo} onCancel={() => setReplyingTo(null)} />
      )}
      <input onSubmit={(content) => sendMessage(content)} />
    </div>
  );
}

// Компонент отображения сообщения с ответом
function MessageBubble({ message }: { message: Message }) {
  const { data: replyMessage } = useQuery({
    queryKey: ['message', message.reply_to_id],
    queryFn: () => api.get(`/messages/${message.reply_to_id}`),
    enabled: !!message.reply_to_id,
  });
  
  return (
    <div className="message">
      {replyMessage && <ReplyPreview message={replyMessage} />}
      <div className="message-content">{message.content}</div>
    </div>
  );
}
```

---

### 5. Typing Indicators (Индикаторы набора текста)

#### `POST /api/v1/presence/typing`

**Request:**
```http
POST /api/v1/presence/typing
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "chat_id": 6,
  "is_typing": true
}
```

**Response:** `204 No Content`

**WebSocket Event:**
```json
{
  "event": "user.typing",
  "data": {
    "chat_id": 6,
    "user_id": 3,
    "is_typing": true
  }
}
```

**Особенности:**
- TTL = 10 секунд (автоматически очищается)
- Рекомендуется отправлять каждые 3-5 секунд пока пользователь печатает
- Отправить `is_typing: false` когда пользователь перестал печатать

#### `GET /api/v1/presence/typing/{chat_id}`

Получить список пользователей, которые сейчас печатают.

**Response:**
```json
[3, 7, 12]  // user_ids
```

**Frontend Hook Example:**
```typescript
function useChatInput(chatId: number) {
  const typingTimeout = useRef<NodeJS.Timeout>();
  const { mutate: setTyping } = useMutation({
    mutationFn: (is_typing: boolean) => 
      api.post('/presence/typing', { chat_id: chatId, is_typing }),
  });
  
  const handleInput = (value: string) => {
    // Отправляем typing: true
    setTyping(true);
    
    // Сбрасываем таймер
    clearTimeout(typingTimeout.current);
    
    // Через 3 секунды без ввода отправляем typing: false
    typingTimeout.current = setTimeout(() => {
      setTyping(false);
    }, 3000);
  };
  
  useEffect(() => {
    return () => {
      setTyping(false);  // Очищаем при размонтировании
      clearTimeout(typingTimeout.current);
    };
  }, []);
  
  return { handleInput };
}

// Компонент отображения typing indicator
function TypingIndicator({ chatId }: { chatId: number }) {
  const { data: typingUsers } = useQuery({
    queryKey: ['typing', chatId],
    queryFn: () => api.get(`/presence/typing/${chatId}`),
    refetchInterval: 2000,  // Обновляем каждые 2 секунды
  });
  
  // Слушаем WebSocket события для real-time обновлений
  useWebSocketEvent('user.typing', (event) => {
    if (event.data.chat_id === chatId) {
      // Обновляем локальный стейт
    }
  });
  
  if (!typingUsers || typingUsers.length === 0) return null;
  
  return <div>Печатает...</div>;
}
```

---

### 6. Online/Offline Status (Статус пользователей)

#### `POST /api/v1/presence/heartbeat`

Обновить статус активности (heartbeat).

**Request:**
```http
POST /api/v1/presence/heartbeat
Authorization: Bearer <access_token>
```

**Response:** `204 No Content`

**Особенности:**
- TTL = 5 минут
- Рекомендуется отправлять каждые 2-3 минуты
- Автоматически устанавливает пользователя в статус "online"

#### `GET /api/v1/presence/{user_id}`

Получить статус пользователя.

**Response:**
```json
{
  "user_id": 3,
  "status": "online",  // online, offline, away
  "last_seen": "2024-11-05T10:00:00Z"
}
```

#### `GET /api/v1/presence/me`

Получить свой статус.

**WebSocket Event:**
```json
{
  "event": "user.presence",
  "data": {
    "user_id": 3,
    "status": "online",
    "timestamp": "2024-11-05T10:00:00Z"
  }
}
```

**Frontend Implementation:**
```typescript
// Heartbeat hook - отправляем каждые 2 минуты
function usePresenceHeartbeat() {
  const { mutate: sendHeartbeat } = useMutation({
    mutationFn: () => api.post('/presence/heartbeat'),
  });
  
  useEffect(() => {
    sendHeartbeat();  // Первый раз сразу
    
    const interval = setInterval(() => {
      sendHeartbeat();
    }, 2 * 60 * 1000);  // Каждые 2 минуты
    
    return () => clearInterval(interval);
  }, []);
}

// Компонент отображения статуса
function UserStatus({ userId }: { userId: number }) {
  const { data: presence } = useQuery({
    queryKey: ['presence', userId],
    queryFn: () => api.get(`/presence/${userId}`),
    refetchInterval: 60000,  // Обновляем каждую минуту
  });
  
  // Слушаем WebSocket для real-time обновлений
  useWebSocketEvent('user.presence', (event) => {
    if (event.data.user_id === userId) {
      // Обновляем кэш
      queryClient.setQueryData(['presence', userId], event.data);
    }
  });
  
  if (!presence) return null;
  
  return (
    <div className="flex items-center gap-2">
      <StatusDot status={presence.status} />
      {presence.status === 'offline' && presence.last_seen && (
        <span>Был(а) {formatRelativeTime(presence.last_seen)}</span>
      )}
    </div>
  );
}
```

---

## 📡 Обновленные WebSocket События

Все события теперь включают новые поля:

### `message.created`
```json
{
  "event": "message.created",
  "data": {
    "id": 123,
    "chat_id": 6,
    "author_id": 3,
    "type": "text",
    "content": "Hello!",
    "payload": null,
    "status": "delivered",
    "ts": "2024-11-05T10:00:00Z",
    "reply_to_id": null,      // НОВОЕ
    "is_deleted": false,      // НОВОЕ
    "deleted_at": null,       // НОВОЕ
    "updated_at": null        // НОВОЕ
  }
}
```

### `message.updated`
```json
{
  "event": "message.updated",
  "data": {
    ...
    "updated_at": "2024-11-05T10:05:00Z"  // НОВОЕ
  }
}
```

### `message.deleted`
```json
{
  "event": "message.deleted",
  "data": {
    ...
    "is_deleted": true,
    "deleted_at": "2024-11-05T10:05:00Z",
    "content": null,
    "payload": null
  }
}
```

### `reaction.added`
```json
{
  "event": "reaction.added",
  "data": {
    "id": 45,
    "message_id": 123,
    "user_id": 3,
    "emoji": "👍",
    "created_at": "2024-11-05T10:00:00Z"
  }
}
```

### `reaction.removed`
```json
{
  "event": "reaction.removed",
  "data": {
    "message_id": 123,
    "user_id": 3,
    "emoji": "👍"
  }
}
```

### `user.typing`
```json
{
  "event": "user.typing",
  "data": {
    "chat_id": 6,
    "user_id": 3,
    "is_typing": true
  }
}
```

### `user.presence`
```json
{
  "event": "user.presence",
  "data": {
    "user_id": 3,
    "status": "online",
    "timestamp": "2024-11-05T10:00:00Z"
  }
}
```

### `chat.deleted`
```json
{
  "event": "chat.deleted",
  "data": {
    "id": 6,
    "deleted_by": 3
  }
}
```

**Описание:**
- Отправляется всем участникам чата когда кто-то удаляет чат
- `id` - ID удаленного чата
- `deleted_by` - ID пользователя, который удалил чат

**Frontend обработка:**
```typescript
// В useRealtimeSubscriptions или WebSocket обработчике
case 'chat.deleted':
  // Удаляем чат из списка
  queryClient.setQueryData<Chat[]>(['chats'], (old) => {
    if (!old) return old;
    return old.filter((chat) => chat.id !== event.data.id);
  });
  
  // Если мы в удаленном чате - перенаправляем на главную
  if (currentChatId === event.data.id) {
    navigate('/chats');
  }
  break;
```

---

## 🔄 Миграция с v1 на v2

### Обновление типов TypeScript

```typescript
// types/message.ts
export interface Message {
  id: number;
  chat_id: number;
  author_id: number | null;
  type: string;
  content: string | null;
  payload: any | null;
  status: "delivered" | "read";
  ts: string;
  
  // ДОБАВИТЬ НОВЫЕ ПОЛЯ
  reply_to_id: number | null;
  is_deleted: boolean;
  deleted_at: string | null;
  updated_at: string | null;
  reactions: Reaction[];
}

export interface Reaction {
  id: number;
  message_id: number;
  user_id: number;
  emoji: string;
  created_at: string;
}

export interface MessageListResponse {
  messages: Message[];
  has_more: boolean;
  next_cursor: number | null;
}
```

### Обновление API адаптера

```typescript
// lib/api.ts
class ApiAdapter {
  // ОБНОВИТЬ: теперь возвращает MessageListResponse
  async getMessages(chatId: number, limit = 50, beforeId?: number) {
    const params = new URLSearchParams({
      chat_id: chatId.toString(),
      limit: limit.toString(),
      ...(beforeId && { before_id: beforeId.toString() }),
    });
    
    const res = await this.http.get<MessageListResponse>(`/messages?${params}`);
    return res.data;
  }
  
  // НОВОЕ: удаление сообщения
  async deleteMessage(messageId: number) {
    await this.http.delete(`/messages/${messageId}`);
  }
  
  // НОВОЕ: добавить реакцию
  async addReaction(messageId: number, emoji: string) {
    const res = await this.http.post<Reaction>(
      `/messages/${messageId}/reactions`,
      { emoji }
    );
    return res.data;
  }
  
  // НОВОЕ: удалить реакцию
  async removeReaction(messageId: number, emoji: string) {
    await this.http.delete(`/messages/${messageId}/reactions/${emoji}`);
  }
  
  // НОВОЕ: typing indicator
  async setTyping(chatId: number, isTyping: boolean) {
    await this.http.post('/presence/typing', {
      chat_id: chatId,
      is_typing: isTyping,
    });
  }
  
  // НОВОЕ: heartbeat
  async sendHeartbeat() {
    await this.http.post('/presence/heartbeat');
  }
  
  // НОВОЕ: получить статус пользователя
  async getUserPresence(userId: number) {
    const res = await this.http.get<UserPresence>(`/presence/${userId}`);
    return res.data;
  }
}
```

### Обновление WebSocket обработчика

```typescript
// hooks/useRealtimeSubscriptions.ts
function useRealtimeSubscriptions() {
  const queryClient = useQueryClient();
  
  useWebSocket({
    onMessage: (event) => {
      switch (event.event) {
        case 'message.created':
        case 'message.updated':
        case 'message.deleted':
          // Обновляем кэш сообщений
          queryClient.invalidateQueries(['messages', event.data.chat_id]);
          break;
          
        // НОВОЕ: реакции
        case 'reaction.added':
        case 'reaction.removed':
          // Обновляем конкретное сообщение
          queryClient.invalidateQueries(['messages', event.data.message_id]);
          break;
          
        // НОВОЕ: typing indicators
        case 'user.typing':
          // Обновляем локальный стейт typing users
          updateTypingUsers(event.data.chat_id, event.data.user_id, event.data.is_typing);
          break;
          
        // НОВОЕ: presence
        case 'user.presence':
          // Обновляем кэш статуса пользователя
          queryClient.setQueryData(['presence', event.data.user_id], event.data);
          break;
          
        // НОВОЕ: удаление чата
        case 'chat.deleted':
          // Удаляем чат из списка
          queryClient.setQueryData<Chat[]>(['chats'], (old) => {
            if (!old) return old;
            return old.filter((chat) => chat.id !== event.data.id);
          });
          break;
      }
    },
  });
}
```

---

## 📋 Checklist для Frontend интеграции

### Обязательные изменения:

- [ ] Обновить TypeScript типы для `Message` (добавить новые поля)
- [ ] Добавить тип `MessageListResponse` для пагинации
- [ ] Обновить hook `useMessages` на `useInfiniteMessages`
- [ ] Обработать `is_deleted` в компоненте сообщения
- [ ] Добавить обработчики новых WebSocket событий

### Новый функционал:

- [ ] Реализовать бесконечный скролл для сообщений
- [ ] Добавить UI для удаления сообщений
- [ ] Реализовать компонент реакций (emoji picker + отображение)
- [ ] Добавить UI для ответов на сообщения
- [ ] Реализовать typing indicators в чате
- [ ] Показывать online/offline статус пользователей
- [ ] Добавить heartbeat для поддержания online статуса

### Опциональные улучшения:

- [ ] Группировка реакций по emoji с счетчиками
- [ ] Анимации для реакций
- [ ] Preview цитируемого сообщения при ответе
- [ ] Переход к цитируемому сообщению по клику
- [ ] Уведомления о новых реакциях
- [ ] Показ "Печатает..." с аватарами пользователей

---

## 🧪 Тестирование

### Тестовые сценарии:

1. **Пагинация:**
   - Загрузить первые 50 сообщений
   - Скроллить вверх и загрузить следующие 50
   - Проверить корректность `next_cursor`

2. **Удаление:**
   - Удалить свое сообщение
   - Проверить, что показывается "Сообщение удалено"
   - Проверить WebSocket событие у другого пользователя

3. **Реакции:**
   - Добавить реакцию на сообщение
   - Убрать реакцию
   - Проверить счетчики реакций
   - Множественные пользователи реагируют на одно сообщение

4. **Ответы:**
   - Ответить на сообщение
   - Проверить отображение цитаты
   - Проверить `reply_to_id` в данных

5. **Typing:**
   - Начать печатать - проверить индикатор у другого пользователя
   - Остановить печатать - индикатор должен исчезнуть
   - Проверить автоматическое исчезновение через 10 секунд

6. **Presence:**
   - Зайти в приложение - статус должен стать "online"
   - Закрыть приложение - через 5 минут статус "offline"
   - Проверить "Был(а) в сети..."

---

## 🔍 Примеры интеграции

### Полный пример чата с новыми функциями:

```typescript
function ChatDetailPage() {
  const { id: chatId } = useParams<{ id: string }>();
  
  // Бесконечный скролл сообщений
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteMessages(Number(chatId));
  
  // Typing indicators
  const { handleInput } = useChatInput(Number(chatId));
  const typingUsers = useTypingUsers(Number(chatId));
  
  // Heartbeat для online статуса
  usePresenceHeartbeat();
  
  // WebSocket подписки
  useRealtimeSubscriptions();
  
  // Состояние для ответа
  const [replyingTo, setReplyingTo] = useState<Message | null>(null);
  
  const messages = data?.pages.flatMap(page => page.messages) ?? [];
  
  return (
    <div className="chat-container">
      <InfiniteScroll
        loadMore={fetchNextPage}
        hasMore={hasNextPage}
        isLoading={isFetchingNextPage}
      >
        {messages.map(message => (
          <MessageBubble
            key={message.id}
            message={message}
            onReply={() => setReplyingTo(message)}
            onDelete={() => deleteMessage(message.id)}
          />
        ))}
      </InfiniteScroll>
      
      {typingUsers.length > 0 && (
        <TypingIndicator users={typingUsers} />
      )}
      
      <ChatInput
        chatId={Number(chatId)}
        replyingTo={replyingTo}
        onCancelReply={() => setReplyingTo(null)}
        onInput={handleInput}
      />
    </div>
  );
}
```

---

## 🚀 Развертывание

### Обновление Backend:

```bash
# 1. Остановить текущий сервер
# 2. Применить миграции
alembic upgrade head

# 3. Перезапустить сервер
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Проверка версии API:

```bash
curl http://localhost:8000/docs
# Проверьте наличие новых endpoints:
# - DELETE /messages/{message_id}
# - POST /messages/{message_id}/reactions
# - POST /presence/typing
# - GET /presence/{user_id}
```

---

## 📞 Поддержка

При возникновении вопросов:
- Проверьте Swagger UI: http://localhost:8000/docs
- Документация в папке `docs/`
- Backend репозиторий: создайте issue

---

**Удачи с интеграцией! 🎉**
