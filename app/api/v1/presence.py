from __future__ import annotations

from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from app.api.dependencies import get_current_user, get_redis
from app.schemas.message import TypingIndicator
from app.schemas.presence import UserPresence
from app.services.presence import PresenceService, TypingService

router = APIRouter()


@router.get("/me", response_model=UserPresence)
async def get_my_presence(
    current_user: int = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
) -> UserPresence:
    """Получить свой онлайн статус"""
    service = PresenceService(redis)
    status_data = await service.get_user_status(current_user)
    return UserPresence(**status_data)


@router.get("/{user_id}", response_model=UserPresence)
async def get_user_presence(
    user_id: int,
    redis: Redis = Depends(get_redis),
) -> UserPresence:
    """Получить онлайн статус пользователя"""
    service = PresenceService(redis)
    status_data = await service.get_user_status(user_id)
    return UserPresence(**status_data)


@router.post("/heartbeat", status_code=204)
async def heartbeat(
    current_user: int = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
) -> None:
    """Обновить статус активности (heartbeat)"""
    service = PresenceService(redis)
    await service.heartbeat(current_user)


@router.post("/typing", status_code=204)
async def set_typing(
    payload: TypingIndicator,
    current_user: int = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
) -> None:
    """Установить/снять индикатор набора текста в чате"""
    service = TypingService(redis)
    if payload.is_typing:
        await service.start_typing(payload.chat_id, current_user)
    else:
        await service.stop_typing(payload.chat_id, current_user)


@router.get("/typing/{chat_id}", response_model=list[int])
async def get_typing_users(
    chat_id: int,
    redis: Redis = Depends(get_redis),
) -> list[int]:
    """Получить список пользователей, печатающих в чате"""
    service = TypingService(redis)
    return await service.get_typing_users(chat_id)
