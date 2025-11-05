# Схема базы данных NODUS_s

## 📊 Обзор

NODUS_s использует PostgreSQL 16 с 4 основными таблицами для хранения данных.

---

## 🗂 Таблицы

### 1. `users` - Пользователи

Хранит информацию о зарегистрированных пользователях.

| Колонка         | Тип          | Описание                    | Constraints           |
|-----------------|--------------|-----------------------------|-----------------------|
| id              | INTEGER      | Уникальный ID               | PRIMARY KEY           |
| email           | VARCHAR(255) | Email пользователя          | UNIQUE, NOT NULL      |
| password_hash   | VARCHAR(255) | Bcrypt хэш пароля           | NOT NULL              |
| display_name    | VARCHAR(255) | Отображаемое имя            | NOT NULL              |
| avatar_url      | VARCHAR(1024)| URL аватара                 | NULLABLE              |
| created_at      | TIMESTAMP    | Дата регистрации            | DEFAULT now()         |

**Индексы:**
- `ix_users_email` (UNIQUE) на `email`

**SQL:**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(1024),
    created_at TIMESTAMP DEFAULT now() NOT NULL
);

CREATE UNIQUE INDEX ix_users_email ON users(email);
```

---

### 2. `chats` - Чаты

Хранит информацию о чатах (групповых и личных).

| Колонка     | Тип          | Описание                    | Constraints           |
|-------------|--------------|-----------------------------|-----------------------|
| id          | INTEGER      | Уникальный ID               | PRIMARY KEY           |
| title       | VARCHAR(255) | Название чата               | NOT NULL              |
| is_group    | BOOLEAN      | Групповой чат или личный    | DEFAULT true          |
| created_at  | TIMESTAMP    | Дата создания               | DEFAULT now()         |

**SQL:**
```sql
CREATE TABLE chats (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    is_group BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP DEFAULT now() NOT NULL
);
```

---

### 3. `chat_members` - Участники чатов

Связь многие-ко-многим между пользователями и чатами.

| Колонка     | Тип          | Описание                    | Constraints           |
|-------------|--------------|-----------------------------|-----------------------|
| id          | INTEGER      | Уникальный ID               | PRIMARY KEY           |
| chat_id     | INTEGER      | ID чата                     | FK -> chats.id        |
| user_id     | INTEGER      | ID пользователя             | FK -> users.id        |
| role        | VARCHAR(50)  | Роль (member, admin)        | DEFAULT 'member'      |
| joined_at   | TIMESTAMP    | Дата присоединения          | DEFAULT now()         |

**Constraints:**
- UNIQUE constraint на `(chat_id, user_id)` - пользователь может быть в чате только один раз
- ON DELETE CASCADE для `chat_id` - при удалении чата удаляются все участники
- ON DELETE CASCADE для `user_id` - при удалении пользователя удаляются все его членства

**Индексы:**
- `ix_chat_members_chat_id` на `chat_id`
- `ix_chat_members_user_id` на `user_id`

**SQL:**
```sql
CREATE TABLE chat_members (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member' NOT NULL,
    joined_at TIMESTAMP DEFAULT now() NOT NULL,
    CONSTRAINT uq_chat_member UNIQUE (chat_id, user_id)
);

CREATE INDEX ix_chat_members_chat_id ON chat_members(chat_id);
CREATE INDEX ix_chat_members_user_id ON chat_members(user_id);
```

---

### 4. `messages` - Сообщения

Хранит все сообщения в чатах.

| Колонка     | Тип          | Описание                    | Constraints           |
|-------------|--------------|-----------------------------|-----------------------|
| id          | INTEGER      | Уникальный ID               | PRIMARY KEY           |
| chat_id     | INTEGER      | ID чата                     | FK -> chats.id        |
| author_id   | INTEGER      | ID автора                   | FK -> users.id        |
| type        | VARCHAR(50)  | Тип сообщения               | NOT NULL              |
| content     | TEXT         | Текстовое содержимое        | NULLABLE              |
| payload     | JSONB        | Дополнительные данные       | NULLABLE              |
| ts          | TIMESTAMP    | Время отправки              | DEFAULT now()         |

**Типы сообщений:**
- `text` - текстовое сообщение
- `voice` - голосовое сообщение
- `system` - системное сообщение

**Constraints:**
- ON DELETE CASCADE для `chat_id` - при удалении чата удаляются все сообщения
- ON DELETE SET NULL для `author_id` - при удалении пользователя его сообщения сохраняются, но author_id становится NULL

**Индексы:**
- `ix_messages_chat_id` на `chat_id`
- `ix_messages_author_id` на `author_id`
- `ix_messages_ts` на `ts`
- `ix_messages_chat_ts` на `(chat_id, ts)` - составной индекс для быстрой выборки сообщений чата

**SQL:**
```sql
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    type VARCHAR(50) NOT NULL,
    content TEXT,
    payload JSONB,
    ts TIMESTAMP DEFAULT now() NOT NULL
);

CREATE INDEX ix_messages_chat_id ON messages(chat_id);
CREATE INDEX ix_messages_author_id ON messages(author_id);
CREATE INDEX ix_messages_ts ON messages(ts);
CREATE INDEX ix_messages_chat_ts ON messages(chat_id, ts);
```

---

## 📐 ER Диаграмма

```
┌─────────────────┐
│     users       │
├─────────────────┤
│ • id (PK)       │
│   email         │
│   password_hash │
│   display_name  │
│   avatar_url    │
│   created_at    │
└────────┬────────┘
         │
         │ 1:N
         │
┌────────▼────────┐         ┌─────────────────┐
│  chat_members   │ N:1     │     chats       │
├─────────────────┤────────►├─────────────────┤
│ • id (PK)       │         │ • id (PK)       │
│   chat_id (FK)  │         │   title         │
│   user_id (FK)  │         │   is_group      │
│   role          │         │   created_at    │
│   joined_at     │         └────────┬────────┘
└─────────────────┘                  │
                                     │ 1:N
                                     │
                            ┌────────▼────────┐
                            │    messages     │
                            ├─────────────────┤
                            │ • id (PK)       │
                            │   chat_id (FK)  │
                            │   author_id (FK)│
                            │   type          │
                            │   content       │
                            │   payload       │
                            │   ts            │
                            └─────────────────┘
```

---

## 🔍 Примеры запросов

### Получить все чаты пользователя
```sql
SELECT c.*
FROM chats c
JOIN chat_members cm ON c.id = cm.chat_id
WHERE cm.user_id = $1
ORDER BY c.created_at DESC;
```

### Получить последние сообщения чата
```sql
SELECT m.*
FROM messages m
WHERE m.chat_id = $1
ORDER BY m.ts DESC
LIMIT 50;
```

### Проверить, является ли пользователь участником чата
```sql
SELECT EXISTS(
    SELECT 1
    FROM chat_members
    WHERE chat_id = $1 AND user_id = $2
);
```

### Получить количество непрочитанных сообщений (будущая функция)
```sql
SELECT COUNT(*)
FROM messages m
WHERE m.chat_id = $1
  AND m.ts > $2  -- последнее время прочтения
  AND m.author_id != $3;  -- не считать свои сообщения
```

---

## 🔐 Безопасность данных

### 1. Пароли
- Хранятся в виде bcrypt хэшей
- Никогда не возвращаются через API
- Минимальная длина: не ограничена на уровне БД (валидация в приложении)

### 2. Каскадные удаления
- Удаление чата → удаляются все сообщения и участники
- Удаление пользователя → удаляются его членства, author_id в сообщениях = NULL

### 3. Foreign Keys
- Все связи защищены ограничениями внешних ключей
- Невозможно создать сообщение в несуществующем чате
- Невозможно добавить несуществующего пользователя в чат

---

## 📈 Оптимизации

### Текущие индексы
1. **users.email** - уникальный индекс для быстрого поиска по email
2. **chat_members (chat_id, user_id)** - для проверки членства
3. **messages (chat_id, ts)** - составной индекс для быстрой выборки истории чата

### Будущие оптимизации
1. Партиционирование таблицы `messages` по времени (monthly partitions)
2. Материализованные представления для статистики
3. Индекс на `messages.payload` с GIN для поиска по JSONB полям
4. Денормализация: хранение last_message в таблице chats

---

## 🔄 Миграции

Все миграции находятся в `alembic/versions/`.

### Текущая версия схемы
- **Revision**: `20240326_0001_initial`
- **Описание**: Начальная схема с таблицами users, chats, chat_members, messages

### Применить миграции
```bash
alembic upgrade head
```

### Откатить к предыдущей версии
```bash
alembic downgrade -1
```

### Создать новую миграцию
```bash
alembic revision --autogenerate -m "description"
```

---

## 💾 Резервное копирование

### Создать backup
```bash
pg_dump -h localhost -U postgres -d nodus > backup_$(date +%Y%m%d).sql
```

### Восстановить из backup
```bash
psql -h localhost -U postgres -d nodus < backup_20240326.sql
```

### Docker volume backup
```bash
docker run --rm -v nodus_s_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
```

---

## 🧪 Тестовые данные

### Создать тестового пользователя
```sql
INSERT INTO users (email, password_hash, display_name)
VALUES ('test@example.com', '$2b$12$...', 'Test User')
RETURNING id;
```

### Создать тестовый чат
```sql
-- Создать чат
INSERT INTO chats (title, is_group)
VALUES ('Test Chat', true)
RETURNING id;

-- Добавить участников
INSERT INTO chat_members (chat_id, user_id, role)
VALUES 
    (1, 1, 'admin'),
    (1, 2, 'member');

-- Добавить сообщения
INSERT INTO messages (chat_id, author_id, type, content)
VALUES 
    (1, 1, 'text', 'Hello!'),
    (1, 2, 'text', 'Hi there!');
```

---

## 📊 Статистика и мониторинг

### Проверить размер таблиц
```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Проверить использование индексов
```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### Медленные запросы
```sql
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

---

## 🔮 Будущие расширения

### Планируемые таблицы
1. **user_settings** - персональные настройки пользователя
2. **read_receipts** - отметки о прочтении сообщений
3. **reactions** - реакции на сообщения
4. **attachments** - метаданные файлов (размер, тип, хэш)
5. **notifications** - системные уведомления

### Планируемые индексы
1. Full-text search на `messages.content`
2. GIN индекс на `messages.payload` для поиска по вложениям
3. Partial индексы для soft-deleted записей

---

**Версия схемы:** 1.0.0  
**Последнее обновление:** 2024-03-26
