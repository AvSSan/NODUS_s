from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.api.dependencies import get_redis

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, redis: Redis = Depends(get_redis)) -> None:
    await websocket.accept()
    pubsub = redis.pubsub()
    await pubsub.subscribe("ws:messages")
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            await websocket.send_text(data)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe("ws:messages")
        await pubsub.close()
