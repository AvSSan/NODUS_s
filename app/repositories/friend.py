from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.domain.models import Friend, User
from app.repositories.base import Repository


class FriendRepository(Repository[Friend]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Friend)

    async def create(self, *, user_id: int, friend_id: int, status: str = "pending") -> Friend:
        """Создать запрос на дружбу"""
        friend = Friend(user_id=user_id, friend_id=friend_id, status=status)
        self.session.add(friend)
        await self.session.flush()
        return friend

    async def get_friendship(self, user_id: int, friend_id: int) -> Friend | None:
        """Получить запись о дружбе между двумя пользователями (в любую сторону)"""
        stmt = select(Friend).where(
            or_(
                and_(Friend.user_id == user_id, Friend.friend_id == friend_id),
                and_(Friend.user_id == friend_id, Friend.friend_id == user_id)
            )
        )
        result = await self.session.scalars(stmt)
        return result.first()

    async def update_status(self, friendship: Friend, status: str) -> Friend:
        """Обновить статус дружбы"""
        friendship.status = status
        await self.session.flush()
        return friendship

    async def list_friends(self, user_id: int, status: str | None = None) -> list[User]:
        """
        Получить список друзей пользователя.
        Возвращает пользователей, с которыми установлена дружба.
        """
        # Находим все записи друзей, где пользователь - инициатор или получатель
        stmt = (
            select(Friend)
            .where(
                or_(
                    Friend.user_id == user_id,
                    Friend.friend_id == user_id
                )
            )
        )
        
        if status is not None:
            stmt = stmt.where(Friend.status == status)
        
        result = await self.session.scalars(stmt)
        friendships = list(result)
        
        # Собираем ID всех друзей
        friend_ids = []
        for friendship in friendships:
            if friendship.user_id == user_id:
                friend_ids.append(friendship.friend_id)
            else:
                friend_ids.append(friendship.user_id)
        
        if not friend_ids:
            return []
        
        # Загружаем пользователей
        user_stmt = select(User).where(User.id.in_(friend_ids))
        users_result = await self.session.scalars(user_stmt)
        return list(users_result)

    async def list_pending_requests(self, user_id: int) -> list[tuple[Friend, User]]:
        """
        Получить список входящих запросов в друзья.
        Возвращает список кортежей (Friend, User) где User - отправитель запроса.
        """
        stmt = (
            select(Friend)
            .where(Friend.friend_id == user_id, Friend.status == "pending")
            .options(joinedload(Friend.user))
        )
        result = await self.session.scalars(stmt)
        friendships = list(result.unique())
        
        return [(f, f.user) for f in friendships]

    async def list_sent_requests(self, user_id: int) -> list[tuple[Friend, User]]:
        """
        Получить список исходящих запросов в друзья.
        Возвращает список кортежей (Friend, User) где User - получатель запроса.
        """
        stmt = (
            select(Friend)
            .where(Friend.user_id == user_id, Friend.status == "pending")
            .options(joinedload(Friend.friend))
        )
        result = await self.session.scalars(stmt)
        friendships = list(result.unique())
        
        return [(f, f.friend) for f in friendships]

    async def delete(self, friendship: Friend) -> None:
        """Удалить дружбу"""
        await self.session.delete(friendship)
        await self.session.flush()
