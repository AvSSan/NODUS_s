from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_redis, get_session
from app.api.utils import require_idempotency
from app.repositories.chat import ChatMemberRepository
from app.repositories.message import MessageRepository
from app.schemas.message import MessageCreate, MessageRead, MessageUpdate
from app.services.idempotency import IdempotencyService
from app.services.message import MessageService

router = APIRouter()


@router.get("", response_model=list[MessageRead])
async def list_messages(
    chat_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: int = Depends(get_current_user),
) -> list[MessageRead]:
    member_repo = ChatMemberRepository(session)
    member = await member_repo.get_member(chat_id=chat_id, user_id=current_user)
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    repo = MessageRepository(session)
    messages = await repo.list_for_chat(chat_id)
    return [MessageRead.model_validate(message) for message in messages]


@router.post("", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def create_message(
    payload: MessageCreate,
    session: AsyncSession = Depends(get_session),
    redis = Depends(get_redis),
    current_user: int = Depends(get_current_user),
    idempotency: tuple[str, IdempotencyService] = Depends(require_idempotency),
) -> MessageRead:
    key, service = idempotency
    member_repo = ChatMemberRepository(session)
    member = await member_repo.get_member(chat_id=payload.chat_id, user_id=current_user)
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    message_service = MessageService(session, redis)
    try:
        message = await message_service.create_message(
            chat_id=payload.chat_id,
            author_id=current_user,
            type=payload.type,
            content=payload.content,
            payload=payload.payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await service.mark_completed(key)
    return MessageRead.model_validate(message)


@router.patch("/{message_id}", response_model=MessageRead)
async def update_message(
    message_id: int,
    payload: MessageUpdate,
    session: AsyncSession = Depends(get_session),
    redis = Depends(get_redis),
    current_user: int = Depends(get_current_user),
    idempotency: tuple[str, IdempotencyService] = Depends(require_idempotency),
) -> MessageRead:
    key, service = idempotency
    repo = MessageRepository(session)
    message = await repo.get(message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if message.author_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    message_service = MessageService(session, redis)
    try:
        message = await message_service.update_message(
            message,
            content=payload.content,
            payload=payload.payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await service.mark_completed(key)
    return MessageRead.model_validate(message)
