import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.modules.reviews import service
from app.modules.reviews.schemas import (
    ReviewCreateRequest,
    ReviewListOut,
    ReviewOut,
    ReviewUpdateRequest,
)

router = APIRouter(prefix="/api/v1", tags=["reviews"])


@router.get("/reviews", response_model=ReviewListOut)
async def list_reviews(
    db: AsyncSession = Depends(get_db),
    listing_id: uuid.UUID | None = Query(None),
    tour_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    if (listing_id is None) == (tour_id is None):
        raise HTTPException(
            400, detail="listing_id yoki tour_id'dan aynan bittasi ko'rsatilishi kerak"
        )
    items, total = await service.list_for_target(
        db, listing_id=listing_id, tour_id=tour_id, page=page, page_size=page_size
    )
    return ReviewListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/reviews/mine", response_model=ReviewListOut)
async def my_reviews(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.list_mine(db, current_user, page, page_size)
    return ReviewListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/reviews", response_model=ReviewOut, status_code=201)
async def create_review(
    payload: ReviewCreateRequest, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await service.create(db, current_user, payload)


@router.patch("/reviews/{review_id}", response_model=ReviewOut)
async def update_review(
    review_id: uuid.UUID,
    payload: ReviewUpdateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.update(db, review_id, current_user, payload)


@router.delete("/reviews/{review_id}", status_code=204)
async def delete_review(
    review_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    await service.delete(db, review_id, current_user)
