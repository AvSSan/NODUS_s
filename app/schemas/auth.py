from __future__ import annotations

from pydantic import BaseModel

from app.schemas.user import UserCreate, UserLogin, UserRead


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: float


class RegisterRequest(UserCreate):
    pass


class LoginRequest(UserLogin):
    pass


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    user: UserRead
    tokens: TokenPair
