from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_session
from app.repositories.user import UserRepository
from app.schemas.user import UserRead, UserUpdateTag

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """Получить информацию о текущем пользователе"""
    repo = UserRepository(session)
    user = await repo.get(current_user)
    return UserRead.model_validate(user)


@router.put("/me/tag", response_model=UserRead)
async def update_user_tag(
    data: UserUpdateTag,
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """Обновить тег текущего пользователя"""
    repo = UserRepository(session)
    
    # Проверяем доступность тега
    is_available = await repo.is_tag_available(data.tag, exclude_user_id=current_user)
    if not is_available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tag is already taken",
        )
    
    # Получаем пользователя и обновляем тег
    user = await repo.get(current_user)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    user = await repo.update_tag(user, data.tag)
    await session.commit()
    await session.refresh(user)
    
    return UserRead.model_validate(user)


@router.get("/tag/{tag}/available")
async def check_tag_availability(
    tag: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    """Проверить доступность тега"""
    repo = UserRepository(session)
    is_available = await repo.is_tag_available(tag)
    return {"available": is_available}


@router.get("/search", response_model=UserRead)
async def search_user_by_tag(
    tag: str,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """Найти пользователя по тегу (@tag)"""
    # Удаляем @ если он присутствует
    tag = tag.strip()
    if tag.startswith('@'):
        tag = tag[1:]
    
    repo = UserRepository(session)
    user = await repo.get_by_tag(tag)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserRead.model_validate(user)
