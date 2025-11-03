from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

ModelT = TypeVar("ModelT")


class Repository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model: type[ModelT]):
        self.session = session
        self.model = model

    async def get(self, obj_id: int) -> ModelT | None:
        return await self.session.get(self.model, obj_id)

    async def list(self, *, offset: int = 0, limit: int = 100) -> list[ModelT]:
        result = await self.session.scalars(select(self.model).offset(offset).limit(limit))
        return list(result)

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)

    async def by_attribute(self, attribute: InstrumentedAttribute, value: object) -> ModelT | None:
        stmt = select(self.model).where(attribute == value)
        result = await self.session.scalars(stmt)
        return result.one_or_none()
