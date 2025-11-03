from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.api.utils import require_idempotency
from app.schemas.auth import AuthResponse, LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserRead
from app.services.auth import AuthService, AuthenticationError
from app.services.idempotency import IdempotencyService

router = APIRouter()


@router.post("/register", response_model=AuthResponse)
async def register(
    payload: RegisterRequest,
    idempotency: tuple[str, IdempotencyService] = Depends(require_idempotency),
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    key, idempotency_service = idempotency
    auth_service = AuthService(session)
    try:
        user = await auth_service.register(
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
            avatar_url=payload.avatar_url,
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    tokens = await auth_service.login(email=payload.email, password=payload.password)
    await idempotency_service.mark_completed(key)
    return AuthResponse(user=UserRead.model_validate(user), tokens=tokens)


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginRequest,
    idempotency: tuple[str, IdempotencyService] = Depends(require_idempotency),
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    key, idempotency_service = idempotency
    auth_service = AuthService(session)
    try:
        tokens = await auth_service.login(email=payload.email, password=payload.password)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    await idempotency_service.mark_completed(key)
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_session)) -> TokenPair:
    auth_service = AuthService(session)
    try:
        tokens = await auth_service.refresh(refresh_token=payload.refresh_token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return tokens
