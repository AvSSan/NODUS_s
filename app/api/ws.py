from __future__ import annotations

import logging
from typing import Dict

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_redis, get_session
from app.core import jwt
from app.core.config import settings
from app.repositories.user import UserRepository

router = APIRouter()
logger = logging.getLogger(__name__)

# Глобальный словарь активных WebSocket соединений: user_id -> WebSocket
active_connections: Dict[int, WebSocket] = {}


async def authenticate_websocket(token: str, session: AsyncSession) -> int | None:
    """Валидация токена и получение user_id"""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        subject = payload.get("sub")
        if subject is None:
            return None
        
        repo = UserRepository(session)
        user = await repo.get(int(subject))
        if user is None:
            return None
        
        return user.id
    except jwt.JWTError:
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    redis: Redis = Depends(get_redis),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    WebSocket endpoint для получения событий в реальном времени.
    Требует токен в query параметре: ws://localhost:8000/ws?token=<access_token>
    """
    # Валидация токена
    user_id = await authenticate_websocket(token, session)
    if user_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning("WebSocket connection rejected: invalid token")
        return
    
    # Принимаем соединение
    await websocket.accept()
    active_connections[user_id] = websocket
    logger.info(f"WebSocket connected: user_id={user_id}")
    
    # Подписываемся на персональный канал пользователя
    pubsub = redis.pubsub()
    channel = f"ws:user:{user_id}"
    await pubsub.subscribe(channel)
    
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            
            await websocket.send_text(data)
            logger.debug(f"Sent WebSocket event to user {user_id}")
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user_id={user_id}")
    finally:
        # Очищаем соединение
        active_connections.pop(user_id, None)
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        logger.info(f"WebSocket cleanup completed for user_id={user_id}")
