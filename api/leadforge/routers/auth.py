import uuid
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select

from leadforge.core.config import get_settings
from leadforge.core.deps import CurrentUser, DbSession
from leadforge.core.ratelimit import limiter
from leadforge.core.security import create_token, decode_token, verify_password
from leadforge.models import User
from leadforge.schemas.auth import RefreshRequest, TokenPair, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

_BAD_LOGIN = HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")


def _tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_token(str(user.id), user.role.value, "access"),
        refresh_token=create_token(str(user.id), user.role.value, "refresh"),
    )


@router.post("/login", response_model=TokenPair)
@limiter.limit(lambda: get_settings().login_rate_limit)
async def login(
    request: Request, db: DbSession, form: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> TokenPair:
    user = await db.scalar(select(User).where(func.lower(User.email) == form.username.lower()))
    if user is None or not user.is_active or not verify_password(form.password, user.password_hash):
        raise _BAD_LOGIN
    return _tokens(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, db: DbSession) -> TokenPair:
    try:
        payload = decode_token(body.refresh_token, "refresh")
        user = await db.get(User, uuid.UUID(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        user = None
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    return _tokens(user)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
