import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.modules.favorites import service
from app.modules.favorites.schemas import FavoriteCreateRequest, FavoriteListOut, FavoriteOut

router = APIRouter(prefix="/api/v1", tags=["favorites"])


@router.post("/favorites", response_model=FavoriteOut, status_code=201)
async def add_favorite(
    payload: FavoriteCreateRequest, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await service.create(db, current_user, payload)


@router.get("/favorites", response_model=FavoriteListOut)
async def list_favorites(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.list_mine(db, current_user, page, page_size)
    return FavoriteListOut(items=items, total=total, page=page, page_size=page_size)


@router.delete("/favorites/{listing_id}", status_code=204)
async def remove_favorite(
    listing_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    await service.remove(db, current_user, listing_id)
