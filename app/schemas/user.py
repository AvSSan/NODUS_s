from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str
    avatar_url: str | None = None

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v:
            raise ValueError('Password cannot be empty')
        # Предупреждение о длинных паролях (bcrypt ограничен 72 байтами)
        if len(v.encode('utf-8')) > 72:
            # Обрезаем до 72 байт для совместимости с bcrypt
            return v.encode('utf-8')[:72].decode('utf-8', errors='ignore')
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    email: EmailStr
    display_name: str
    tag: str
    avatar_url: str | None
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class UserUpdateTag(BaseModel):
    tag: str

    @field_validator('tag')
    @classmethod
    def validate_tag(cls, v: str) -> str:
        # Удаляем @ если он присутствует в начале
        v = v.strip()
        if v.startswith('@'):
            v = v[1:]
        
        # Проверяем длину
        if len(v) < 3:
            raise ValueError('Tag must be at least 3 characters')
        if len(v) > 32:
            raise ValueError('Tag must be at most 32 characters')
        
        # Проверяем формат: только латинские буквы, цифры и подчеркивания
        if not v.replace('_', '').replace('.', '').isalnum():
            raise ValueError('Tag can only contain letters, numbers, underscores and dots')
        
        # Не может начинаться или заканчиваться на точку или подчеркивание
        if v[0] in '._' or v[-1] in '._':
            raise ValueError('Tag cannot start or end with . or _')
        
        return v.lower()  # Приводим к нижнему регистру
