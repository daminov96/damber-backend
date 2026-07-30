import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, CurrentUserOptional, require_role
from app.core.storage import StoragePort, get_storage
from app.modules.admin import service as admin_service
from app.modules.admin.models import AuditAction
from app.modules.admin.schemas import RejectRequest
from app.modules.listings.models import Region
from app.modules.tours import service
from app.modules.tours.models import TourSortOption
from app.modules.tours.schemas import (
    TourBookingCreateRequest,
    TourBookingListOut,
    TourBookingOut,
    TourCreateRequest,
    TourListOut,
    TourOut,
    TourUpdateRequest,
)
from app.modules.users.models import User, UserRole

router = APIRouter(prefix="/api/v1", tags=["tours"])


@router.get("/tours", response_model=TourListOut)
async def list_tours(
    db: AsyncSession = Depends(get_db),
    query: str | None = Query(None),
    region: Region | None = Query(None),
    category: str | None = Query(None),
    nights_min: int | None = Query(None, ge=0),
    nights_max: int | None = Query(None, ge=0),
    sort: TourSortOption = Query(TourSortOption.rating),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.search(
        db,
        query=query,
        region=region,
        category=category,
        nights_min=nights_min,
        nights_max=nights_max,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return TourListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/tours/mine", response_model=list[TourOut])
async def my_tours(
    current_user: Annotated[User, Depends(require_role(UserRole.B2B, UserRole.ADMIN))],
    db: AsyncSession = Depends(get_db),
):
    return await service.list_mine(db, current_user)


@router.get("/tours/{tour_id}", response_model=TourOut)
async def get_tour(
    tour_id: uuid.UUID, current_user: CurrentUserOptional, db: AsyncSession = Depends(get_db)
):
    return await service.get_by_id(db, tour_id, current_user)


@router.post("/tours", response_model=TourOut, status_code=201)
async def create_tour(
    payload: TourCreateRequest,
    current_user: Annotated[User, Depends(require_role(UserRole.B2B))],
    db: AsyncSession = Depends(get_db),
):
    return await service.create(db, current_user, payload)


@router.patch("/tours/{tour_id}", response_model=TourOut)
async def update_tour(
    tour_id: uuid.UUID,
    payload: TourUpdateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.update(db, tour_id, current_user, payload)


@router.delete("/tours/{tour_id}", status_code=204)
async def delete_tour(
    tour_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    await service.delete(db, tour_id, current_user)


@router.post("/tours/{tour_id}/photos", response_model=TourOut)
async def upload_tour_photos(
    tour_id: uuid.UUID,
    current_user: CurrentUser,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    return await service.add_photos(db, tour_id, current_user, files, storage)


@router.delete("/tours/{tour_id}/photos/{photo_id}", status_code=204)
async def delete_tour_photo(
    tour_id: uuid.UUID,
    photo_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    await service.delete_photo(db, tour_id, photo_id, current_user, storage)


@router.post("/admin/tours/{tour_id}/approve", response_model=TourOut)
async def approve_tour(
    tour_id: uuid.UUID,
    admin: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: AsyncSession = Depends(get_db),
):
    tour = await service.approve(db, tour_id)
    await admin_service.log_action(db, admin, AuditAction.tour_approve, "tour", tour_id)
    return tour


@router.post("/admin/tours/{tour_id}/reject", response_model=TourOut)
async def reject_tour(
    tour_id: uuid.UUID,
    payload: RejectRequest,
    admin: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: AsyncSession = Depends(get_db),
):
    tour = await service.reject(db, tour_id, payload.reason)
    await admin_service.log_action(
        db, admin, AuditAction.tour_reject, "tour", tour_id, payload.reason
    )
    return tour


@router.post("/tours/{tour_id}/bookings", response_model=TourBookingOut, status_code=201)
async def create_tour_booking(
    tour_id: uuid.UUID,
    payload: TourBookingCreateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.create_booking(db, current_user, tour_id, payload)


@router.get("/tours/{tour_id}/bookings", response_model=TourBookingListOut)
async def list_tour_bookings(
    tour_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.list_tour_bookings(db, tour_id, current_user, page, page_size)
    return TourBookingListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/tour-bookings/mine", response_model=TourBookingListOut)
async def my_tour_bookings(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.list_my_bookings(db, current_user, page, page_size)
    return TourBookingListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/tour-bookings/{booking_id}/confirm", response_model=TourBookingOut)
async def confirm_tour_booking(
    booking_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await service.confirm_booking(db, booking_id, current_user)


@router.post("/tour-bookings/{booking_id}/reject", response_model=TourBookingOut)
async def reject_tour_booking(
    booking_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await service.reject_booking(db, booking_id, current_user)
