from __future__ import annotations

from datetime import datetime, timedelta

from redis.asyncio import Redis


class IdempotencyService:
    def __init__(self, redis: Redis, prefix: str = "idempotency"):
        self.redis = redis
        self.prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    async def check_and_store(self, key: str, value: str, ttl: timedelta) -> bool:
        redis_key = self._key(key)
        was_set = await self.redis.set(redis_key, value, nx=True, ex=int(ttl.total_seconds()))
        return bool(was_set)

    async def get(self, key: str) -> str | None:
        return await self.redis.get(self._key(key))

    async def mark_completed(self, key: str, ttl: timedelta | None = timedelta(hours=24)) -> None:
        redis_key = self._key(key)
        if ttl is not None:
            await self.redis.set(redis_key, "completed", ex=int(ttl.total_seconds()), xx=True)
        else:
            await self.redis.set(redis_key, "completed", xx=True)


class IdempotencyRecord(BaseException):
    def __init__(self, value: str):
        super().__init__(value)
        self.value = value
        self.timestamp = datetime.utcnow()
