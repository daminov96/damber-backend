from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.modules.users import service
from app.modules.users.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.post("/auth/register", response_model=TokenPair)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await service.register(db, payload)
    return service.issue_tokens(user)


@router.post("/auth/login", response_model=TokenPair)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await service.authenticate(db, payload)
    return service.issue_tokens(user)


@router.post("/auth/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    claims = decode_token(payload.refresh_token, "refresh")
    user = await service.get_by_id(db, claims["sub"])
    if not user or user.is_banned:
        raise UnauthorizedError("Foydalanuvchi topilmadi")
    return service.issue_tokens(user)


@router.get("/users/me", response_model=UserOut)
async def me(current_user: CurrentUser):
    return current_user
