from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_redis, get_session
from app.api.utils import require_idempotency
from app.repositories.chat import ChatMemberRepository
from app.repositories.message import MessageRepository
from app.schemas.message import (
    MessageCreate,
    MessageListResponse,
    MessageRead,
    MessageUpdate,
    ReactionCreate,
    ReactionRead,
)
from app.services.idempotency import IdempotencyService
from app.services.message import MessageService

router = APIRouter()


@router.get("", response_model=MessageListResponse)
async def list_messages(
    chat_id: int,
    limit: int = 50,
    before_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: int = Depends(get_current_user),
) -> MessageListResponse:
    """Получить список сообщений с пагинацией (cursor-based)"""
    member_repo = ChatMemberRepository(session)
    member = await member_repo.get_member(chat_id=chat_id, user_id=current_user)
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    repo = MessageRepository(session)
    messages_raw = await repo.list_for_chat(chat_id, limit=limit, before_id=before_id)
    
    # Определяем, есть ли еще сообщения
    has_more = len(messages_raw) > limit
    messages = messages_raw[:limit]  # Берем только limit сообщений
    
    # Определяем next_cursor для следующей страницы
    next_cursor = messages[-1].id if has_more and messages else None
    
    return MessageListResponse(
        messages=[MessageRead.model_validate(msg) for msg in messages],
        has_more=has_more,
        next_cursor=next_cursor,
    )


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
            reply_to_id=payload.reply_to_id,
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


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: int,
    session: AsyncSession = Depends(get_session),
    redis = Depends(get_redis),
    current_user: int = Depends(get_current_user),
) -> None:
    """Удалить сообщение (soft delete)"""
    repo = MessageRepository(session)
    message = await repo.get(message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if message.author_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    message_service = MessageService(session, redis)
    try:
        await message_service.delete_message(message)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{message_id}/reactions", response_model=ReactionRead, status_code=status.HTTP_201_CREATED)
async def add_reaction(
    message_id: int,
    payload: ReactionCreate,
    session: AsyncSession = Depends(get_session),
    redis = Depends(get_redis),
    current_user: int = Depends(get_current_user),
) -> ReactionRead:
    """Добавить реакцию на сообщение"""
    repo = MessageRepository(session)
    message = await repo.get(message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    
    # Проверяем доступ к чату
    member_repo = ChatMemberRepository(session)
    member = await member_repo.get_member(chat_id=message.chat_id, user_id=current_user)
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    message_service = MessageService(session, redis)
    try:
        reaction = await message_service.add_reaction(message_id, current_user, payload.emoji)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    
    return ReactionRead.model_validate(reaction)


@router.delete("/{message_id}/reactions/{emoji}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_reaction(
    message_id: int,
    emoji: str,
    session: AsyncSession = Depends(get_session),
    redis = Depends(get_redis),
    current_user: int = Depends(get_current_user),
) -> None:
    """Удалить реакцию с сообщения"""
    repo = MessageRepository(session)
    message = await repo.get(message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    
    # Проверяем доступ к чату
    member_repo = ChatMemberRepository(session)
    member = await member_repo.get_member(chat_id=message.chat_id, user_id=current_user)
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    message_service = MessageService(session, redis)
    await message_service.remove_reaction(message_id, current_user, emoji)
