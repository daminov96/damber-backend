import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, CurrentUserOptional, require_role
from app.modules.bookings import service
from app.modules.bookings.models import BookingStatus
from app.modules.bookings.schemas import (
    BookingCreateRequest,
    BookingListOut,
    BookingOut,
    BookingQuoteOut,
    BookingRejectRequest,
)
from app.modules.users.models import User, UserRole

router = APIRouter(prefix="/api/v1", tags=["bookings"])


@router.get("/bookings/quote", response_model=BookingQuoteOut)
async def get_quote(
    listing_id: uuid.UUID,
    check_in: date,
    check_out: date,
    guests: int,
    _current_user: CurrentUserOptional,
    db: AsyncSession = Depends(get_db),
    promo_code: str | None = Query(None),
):
    return await service.quote(db, listing_id, check_in, check_out, guests, promo_code)


@router.post("/bookings", response_model=BookingOut, status_code=201)
async def create_booking(
    payload: BookingCreateRequest, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await service.create(db, current_user, payload)


@router.get("/bookings/mine", response_model=BookingListOut)
async def my_bookings(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.list_mine(db, current_user, page, page_size)
    return BookingListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/bookings/host", response_model=BookingListOut)
async def host_bookings(
    current_user: Annotated[User, Depends(require_role(UserRole.B2B, UserRole.ADMIN))],
    db: AsyncSession = Depends(get_db),
    status: BookingStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.list_for_host(db, current_user, status, page, page_size)
    return BookingListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/bookings/{booking_id}", response_model=BookingOut)
async def get_booking(
    booking_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await service.get_by_id(db, booking_id, current_user)


@router.post("/bookings/{booking_id}/confirm", response_model=BookingOut)
async def confirm_booking(
    booking_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await service.confirm(db, booking_id, current_user)


@router.post("/bookings/{booking_id}/reject", response_model=BookingOut)
async def reject_booking(
    booking_id: uuid.UUID,
    payload: BookingRejectRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.reject(db, booking_id, current_user, payload.reason)


@router.post("/bookings/{booking_id}/complete", response_model=BookingOut)
async def complete_booking(
    booking_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await service.complete(db, booking_id, current_user)


@router.post("/bookings/{booking_id}/cancel", response_model=BookingOut)
async def cancel_booking(
    booking_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await service.cancel(db, booking_id, current_user)


@router.post("/bookings/{booking_id}/restore", response_model=BookingOut)
async def restore_booking(
    booking_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await service.restore(db, booking_id, current_user)
