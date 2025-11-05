from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import attachments, auth, chats, messages, presence, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/v1/users", tags=["users"])
api_router.include_router(chats.router, prefix="/v1/chats", tags=["chats"])
api_router.include_router(messages.router, prefix="/v1/messages", tags=["messages"])
api_router.include_router(attachments.router, prefix="/v1/attachments", tags=["attachments"])
api_router.include_router(presence.router, prefix="/v1/presence", tags=["presence"])
