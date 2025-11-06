from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_session
from app.repositories.chat import ChatMemberRepository, ChatRepository
from app.repositories.pinned_chat import PinnedChatRepository
from app.schemas.chat import ChatRead
from app.schemas.pinned_chat import PinChatRequest, PinnedChatsResponse

router = APIRouter()

# Константа: максимальное количество закрепленных чатов
MAX_PINNED_CHATS = 5


@router.post("", status_code=status.HTTP_201_CREATED)
async def pin_chat(
    payload: PinChatRequest,
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Закрепить чат"""
    # Проверяем, что чат существует и пользователь является его участником
    chat_repo = ChatRepository(session)
    chat = await chat_repo.get(payload.chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )
    
    member_repo = ChatMemberRepository(session)
    member = await member_repo.get_member(chat_id=payload.chat_id, user_id=current_user)
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this chat",
        )
    
    pinned_repo = PinnedChatRepository(session)
    
    # Проверяем, не закреплен ли уже чат
    existing = await pinned_repo.get_pinned(current_user, payload.chat_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat is already pinned",
        )
    
    # Проверяем лимит закрепленных чатов
    count = await pinned_repo.count_pinned(current_user)
    if count >= MAX_PINNED_CHATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_PINNED_CHATS} chats can be pinned",
        )
    
    # Получаем следующий порядок закрепления
    max_order = await pinned_repo.get_max_pin_order(current_user)
    pin_order = max_order + 1
    
    # Создаем закрепление
    await pinned_repo.create(user_id=current_user, chat_id=payload.chat_id, pin_order=pin_order)
    await session.commit()
    
    return {"message": "Chat pinned successfully"}


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unpin_chat(
    chat_id: int,
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Открепить чат"""
    pinned_repo = PinnedChatRepository(session)
    
    # Проверяем, закреплен ли чат
    pinned = await pinned_repo.get_pinned(current_user, chat_id)
    if pinned is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat is not pinned",
        )
    
    # Удаляем закрепление
    await pinned_repo.unpin(pinned)
    
    # Переупорядочиваем оставшиеся закрепленные чаты
    await pinned_repo.reorder_pins(current_user)
    
    await session.commit()


@router.get("", response_model=PinnedChatsResponse)
async def list_pinned_chats(
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PinnedChatsResponse:
    """Получить список закрепленных чатов"""
    from app.repositories.message import MessageRepository
    from app.repositories.message_read import MessageReadRepository
    
    pinned_repo = PinnedChatRepository(session)
    message_repo = MessageRepository(session)
    message_read_repo = MessageReadRepository(session)
    
    chats = await pinned_repo.list_pinned_chats(current_user)
    count = len(chats)
    
    result = []
    for chat in chats:
        chat_dict = {
            'id': chat.id,
            'title': chat.title,
            'is_group': chat.is_group,
            'created_at': chat.created_at,
            'participants': [member.user for member in chat.members],
        }
        
        # Получаем последнее сообщение
        last_message = await message_repo.get_last_message(chat.id)
        if last_message:
            chat_dict['lastMessagePreview'] = last_message.content or '[медиа]'
            chat_dict['updatedAt'] = last_message.ts.isoformat()
            
            # Автор уже загружен через joinedload
            if last_message.author:
                chat_dict['lastMessageAuthor'] = last_message.author.display_name
        
        # Получаем количество непрочитанных сообщений
        unread_count = await message_read_repo.get_unread_count(chat.id, current_user)
        chat_dict['unreadCount'] = unread_count
        
        result.append(ChatRead.model_validate(chat_dict))
    
    return PinnedChatsResponse(
        chats=result,
        total=count,
        max_pins=MAX_PINNED_CHATS,
    )
