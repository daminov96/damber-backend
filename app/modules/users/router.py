from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.modules.users import service
from app.modules.users.schemas import LoginRequest, RegisterRequest, TokenPair, UserOut

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.post("/auth/register", response_model=TokenPair)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await service.register(db, payload)
    return service.issue_tokens(user)


@router.post("/auth/login", response_model=TokenPair)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await service.authenticate(db, payload)
    return service.issue_tokens(user)


@router.get("/users/me", response_model=UserOut)
async def me(current_user: CurrentUser):
    return current_user
