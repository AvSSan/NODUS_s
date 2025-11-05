from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserRead


class ChatMemberRead(BaseModel):
    id: int
    user: UserRead
    role: str
    joined_at: datetime

    model_config = {"from_attributes": True}


class ChatCreate(BaseModel):
    title: str
    is_group: bool = True
    member_ids: list[int]


class ChatUpdate(BaseModel):
    title: str | None = None


class ChatRead(BaseModel):
    id: int
    title: str
    is_group: bool
    created_at: datetime
    participants: list[UserRead] = []

    model_config = {"from_attributes": True}
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Переопределяем model_validate для извлечения participants из members"""
        if hasattr(obj, 'members'):
            # Извлекаем пользователей из ChatMember relationship
            participants = [member.user for member in obj.members]
            # Создаем словарь с данными
            data = {
                'id': obj.id,
                'title': obj.title,
                'is_group': obj.is_group,
                'created_at': obj.created_at,
                'participants': [UserRead.model_validate(user) for user in participants]
            }
            return super().model_validate(data, **kwargs)
        return super().model_validate(obj, **kwargs)


class DirectMessageCreate(BaseModel):
    user_id: int
