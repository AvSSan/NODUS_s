from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_session
from app.repositories.friend import FriendRepository
from app.repositories.user import UserRepository
from app.schemas.friend import FriendRequest, FriendStatusUpdate, FriendWithUser
from app.schemas.user import UserRead

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def send_friend_request(
    payload: FriendRequest,
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Отправить запрос на добавление в друзья"""
    # Проверяем, что пользователь не добавляет сам себя
    if payload.friend_id == current_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add yourself as a friend",
        )
    
    # Проверяем, что пользователь существует
    user_repo = UserRepository(session)
    friend_user = await user_repo.get(payload.friend_id)
    if friend_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Проверяем, нет ли уже запроса/дружбы
    friend_repo = FriendRepository(session)
    existing = await friend_repo.get_friendship(current_user, payload.friend_id)
    if existing is not None:
        if existing.status == "accepted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already friends",
            )
        elif existing.status == "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Friend request already sent",
            )
        elif existing.status == "blocked":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot send friend request",
            )
    
    # Создаем запрос на дружбу
    await friend_repo.create(user_id=current_user, friend_id=payload.friend_id, status="pending")
    await session.commit()
    
    return {"message": "Friend request sent"}


@router.get("/requests/incoming", response_model=list[FriendWithUser])
async def get_incoming_friend_requests(
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[FriendWithUser]:
    """Получить список входящих запросов в друзья"""
    friend_repo = FriendRepository(session)
    requests = await friend_repo.list_pending_requests(current_user)
    
    return [
        FriendWithUser(
            friendship=friendship,
            user=UserRead.model_validate(user)
        )
        for friendship, user in requests
    ]


@router.get("/requests/outgoing", response_model=list[FriendWithUser])
async def get_outgoing_friend_requests(
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[FriendWithUser]:
    """Получить список исходящих запросов в друзья"""
    friend_repo = FriendRepository(session)
    requests = await friend_repo.list_sent_requests(current_user)
    
    return [
        FriendWithUser(
            friendship=friendship,
            user=UserRead.model_validate(user)
        )
        for friendship, user in requests
    ]


@router.patch("/{friend_id}")
async def update_friend_status(
    friend_id: int,
    payload: FriendStatusUpdate,
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """
    Принять или заблокировать запрос в друзья.
    Только получатель запроса может изменить его статус.
    """
    if payload.status not in ["accepted", "blocked"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be 'accepted' or 'blocked'",
        )
    
    friend_repo = FriendRepository(session)
    friendship = await friend_repo.get_friendship(current_user, friend_id)
    
    if friendship is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found",
        )
    
    # Проверяем, что запрос был отправлен другим пользователем к текущему
    if friendship.friend_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only respond to requests sent to you",
        )
    
    if friendship.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Friend request is not pending",
        )
    
    await friend_repo.update_status(friendship, payload.status)
    await session.commit()
    
    action = "accepted" if payload.status == "accepted" else "blocked"
    return {"message": f"Friend request {action}"}


@router.get("", response_model=list[UserRead])
async def list_friends(
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[UserRead]:
    """Получить список друзей"""
    friend_repo = FriendRepository(session)
    friends = await friend_repo.list_friends(current_user, status="accepted")
    
    return [UserRead.model_validate(user) for user in friends]


@router.delete("/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_friend(
    friend_id: int,
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Удалить из друзей или отменить запрос"""
    friend_repo = FriendRepository(session)
    friendship = await friend_repo.get_friendship(current_user, friend_id)
    
    if friendship is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friendship not found",
        )
    
    await friend_repo.delete(friendship)
    await session.commit()
