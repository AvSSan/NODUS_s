# 🐛 Backend Bug Report - Ошибка 500 при создании сообщений

## Проблема

При отправке сообщения через `POST /api/v1/messages` backend возвращает ошибку **500 Internal Server Error**.

### Детали ошибки

```json
{
  "detail": "Internal server error",
  "error": "1 validation error for MessageRead\nreactions\n Error extracting attribute: MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here. Was IO attempted in an unexpected place? (Background on this error at: https://sqlalche.me/e/20/xd2s)"
}
```

## Причина

SQLAlchemy пытается **синхронно** загрузить связанное поле `reactions` в модели `Message`, но это требует **асинхронного** контекста (`greenlet`).

Ошибка происходит при сериализации ответа в Pydantic модель `MessageRead`.

## Что работает

✅ Сообщение **успешно создается** в базе данных  
✅ WebSocket событие `message.created` **корректно отправляется**  
✅ Фронтенд **получает сообщение** через WebSocket  

❌ HTTP ответ возвращает 500 вместо созданного сообщения

## Решение

### Вариант 1: Eager Loading (рекомендуется)

В эндпоинте создания сообщения загрузите `reactions` явно:

```python
from sqlalchemy.orm import selectinload

@router.post("/messages", response_model=MessageRead)
async def create_message(
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Создание сообщения
    message = Message(**message_data.dict(), author_id=current_user.id)
    db.add(message)
    await db.commit()
    
    # Явная загрузка связанных данных
    await db.refresh(message, ["reactions"])
    
    # Или через selectinload
    stmt = select(Message).where(Message.id == message.id).options(
        selectinload(Message.reactions)
    )
    result = await db.execute(stmt)
    message = result.scalar_one()
    
    return message
```

### Вариант 2: Lazy Loading Configuration

Настройте relationship для ленивой загрузки:

```python
# models.py
class Message(Base):
    __tablename__ = "messages"
    
    # ...
    
    reactions = relationship(
        "Reaction",
        back_populates="message",
        lazy="selectin"  # Автоматическая асинхронная загрузка
    )
```

### Вариант 3: Pydantic from_orm

Используйте `from_orm` с явной загрузкой:

```python
from pydantic import BaseModel

class MessageRead(BaseModel):
    id: int
    content: str
    reactions: List[ReactionRead] = []
    
    class Config:
        from_attributes = True
    
    @classmethod
    async def from_message(cls, message: Message, db: AsyncSession):
        # Явно загружаем reactions
        await db.refresh(message, ["reactions"])
        return cls.model_validate(message)
```

## Временное решение на фронтенде

Фронтенд был обновлен для обработки этой ошибки:

1. ✅ Оптимистичное обновление UI
2. ✅ WebSocket заменяет оптимистичное сообщение на реальное
3. ✅ Если WebSocket не пришло за 2 секунды - откат изменений
4. ✅ Предотвращение дубликатов сообщений

**Но это НЕ исправляет проблему на backend!**

## Проверка исправления

После исправления backend проверьте:

```bash
curl -X POST http://localhost:8000/api/v1/messages \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "chat_id": 2,
    "type": "text",
    "content": "Test message"
  }'
```

Ожидаемый результат: **200 OK** с полным объектом сообщения, включая пустой массив `reactions`.

## Дополнительная информация

- **SQLAlchemy AsyncIO Documentation**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **Error Reference**: https://sqlalche.me/e/20/xd2s
- **Pydantic v2 with SQLAlchemy**: https://docs.pydantic.dev/latest/concepts/models/#arbitrary-class-instances

---

**Приоритет:** 🔴 HIGH  
**Затронутые функции:** Отправка сообщений  
**Версия:** Backend v2.0
