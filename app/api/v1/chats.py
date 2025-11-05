from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_redis, get_session
from app.api.utils import require_idempotency
from app.domain.models import Chat
from app.repositories.chat import ChatMemberRepository, ChatRepository
from app.schemas.chat import ChatCreate, ChatRead, ChatUpdate, DirectMessageCreate
from app.services.chat import ChatService
from app.services.idempotency import IdempotencyService
from app.services.message import MessageService

router = APIRouter()


async def get_chat_or_404(chat_id: int, session: AsyncSession) -> Chat:
    repo = ChatRepository(session)
    chat = await repo.get(chat_id)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return chat


@router.get("", response_model=list[ChatRead])
async def list_chats(
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ChatRead]:
    repo = ChatRepository(session)
    chats = await repo.list_for_user(current_user)
    return [ChatRead.model_validate(chat) for chat in chats]


@router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
async def create_chat(
    payload: ChatCreate,
    current_user: int = Depends(get_current_user),
    idempotency: tuple[str, IdempotencyService] = Depends(require_idempotency),
    session: AsyncSession = Depends(get_session),
) -> ChatRead:
    key, service = idempotency
    chat_service = ChatService(session)
    member_ids = list(dict.fromkeys([current_user, *payload.member_ids]))
    chat = await chat_service.create_chat(title=payload.title, is_group=payload.is_group, member_ids=member_ids)
    await service.mark_completed(key)
    return ChatRead.model_validate(chat)


@router.get("/{chat_id}", response_model=ChatRead)
async def get_chat(
    chat_id: int,
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatRead:
    chat = await get_chat_or_404(chat_id, session)
    member_repo = ChatMemberRepository(session)
    member = await member_repo.get_member(chat_id=chat_id, user_id=current_user)
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return ChatRead.model_validate(chat)


@router.patch("/{chat_id}", response_model=ChatRead)
async def update_chat(
    chat_id: int,
    payload: ChatUpdate,
    current_user: int = Depends(get_current_user),
    idempotency: tuple[str, IdempotencyService] = Depends(require_idempotency),
    session: AsyncSession = Depends(get_session),
) -> ChatRead:
    key, service = idempotency
    chat = await get_chat_or_404(chat_id, session)
    member_repo = ChatMemberRepository(session)
    member = await member_repo.get_member(chat_id=chat_id, user_id=current_user)
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    chat_service = ChatService(session)
    chat = await chat_service.update_chat(chat, title=payload.title)
    await service.mark_completed(key)
    return ChatRead.model_validate(chat)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: int,
    current_user: int = Depends(get_current_user),
    idempotency: tuple[str, IdempotencyService] = Depends(require_idempotency),
    session: AsyncSession = Depends(get_session),
) -> None:
    key, service = idempotency
    chat = await get_chat_or_404(chat_id, session)
    member_repo = ChatMemberRepository(session)
    member = await member_repo.get_member(chat_id=chat_id, user_id=current_user)
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    chat_service = ChatService(session)
    await chat_service.delete_chat(chat)
    await service.mark_completed(key)


@router.post("/direct", response_model=ChatRead, status_code=status.HTTP_200_OK)
async def create_or_get_direct_message(
    payload: DirectMessageCreate,
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatRead:
    """Создать или получить личную переписку с пользователем"""
    chat_service = ChatService(session)
    
    # Проверяем, что пользователь не пытается создать чат с самим собой
    if payload.user_id == current_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create direct message with yourself",
        )
    
    try:
        chat = await chat_service.create_or_get_direct_message(current_user, payload.user_id)
        return ChatRead.model_validate(chat)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{chat_id}/read", status_code=status.HTTP_200_OK)
async def mark_chat_as_read(
    chat_id: int,
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis = Depends(get_redis),
) -> dict[str, list[int]]:
    """
    Отметить все непрочитанные сообщения в чате как прочитанные.
    Возвращает список ID прочитанных сообщений и отправляет WebSocket событие.
    """
    # Проверяем доступ к чату
    member_repo = ChatMemberRepository(session)
    member = await member_repo.get_member(chat_id=chat_id, user_id=current_user)
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Отмечаем сообщения как прочитанные
    message_service = MessageService(session, redis)
    message_ids = await message_service.mark_messages_as_read(chat_id, current_user)
    
    return {"message_ids": message_ids}
