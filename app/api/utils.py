from __future__ import annotations

from datetime import timedelta

from fastapi import Depends, Header, HTTPException, status

from app.api.dependencies import get_idempotency_service
from app.services.idempotency import IdempotencyService


async def require_idempotency(
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    idempotency: IdempotencyService = Depends(get_idempotency_service),
) -> tuple[str, IdempotencyService]:
    if idempotency_key is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Idempotency-Key header")
    stored = await idempotency.get(idempotency_key)
    if stored is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate request")
    stored = await idempotency.check_and_store(idempotency_key, "pending", timedelta(minutes=5))
    if not stored:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate request")
    return idempotency_key, idempotency
