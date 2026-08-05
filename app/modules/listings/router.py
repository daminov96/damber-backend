import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, CurrentUserOptional, require_role
from app.core.storage import StoragePort, get_storage
from app.modules.admin import service as admin_service
from app.modules.admin.models import AuditAction
from app.modules.admin.schemas import RejectRequest
from app.modules.listings import service
from app.modules.listings.models import ListingType, Region, SortOption, UploadFileField
from app.modules.listings.schemas import (
    ListingCreateRequest,
    ListingListOut,
    ListingOut,
    ListingUpdateRequest,
    UploadFileOut,
)
from app.modules.users.models import User, UserRole

router = APIRouter(prefix="/api/v1", tags=["listings"])


@router.get("/listings", response_model=ListingListOut)
async def list_listings(
    db: AsyncSession = Depends(get_db),
    type: ListingType | None = Query(None),
    region: Region | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    amenities: list[str] | None = Query(None),
    guests: int | None = Query(None, ge=1),
    query: str | None = Query(None),
    min_rating: float | None = Query(None, ge=0, le=5),
    sort: SortOption = Query(SortOption.newest),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.search(
        db,
        type=type,
        region=region,
        min_price=min_price,
        max_price=max_price,
        amenities=amenities,
        guests=guests,
        query=query,
        min_rating=min_rating,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return ListingListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/listings/mine", response_model=list[ListingOut])
async def my_listings(
    current_user: Annotated[User, Depends(require_role(UserRole.B2B))],
    db: AsyncSession = Depends(get_db),
):
    return await service.list_mine(db, current_user)


@router.get("/listings/{listing_id}", response_model=ListingOut)
async def get_listing(
    listing_id: uuid.UUID,
    current_user: CurrentUserOptional,
    db: AsyncSession = Depends(get_db),
):
    return await service.get_by_id(db, listing_id, current_user)


@router.post("/listings", response_model=ListingOut, status_code=201)
async def create_listing(
    payload: ListingCreateRequest,
    current_user: Annotated[User, Depends(require_role(UserRole.B2B))],
    db: AsyncSession = Depends(get_db),
):
    return await service.create(db, current_user, payload)


@router.patch("/listings/{listing_id}", response_model=ListingOut)
async def update_listing(
    listing_id: uuid.UUID,
    payload: ListingUpdateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.update(db, listing_id, current_user, payload)


@router.delete("/listings/{listing_id}", status_code=204)
async def delete_listing(
    listing_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    await service.delete(db, listing_id, current_user, storage)


@router.post("/listings/{listing_id}/pause", response_model=ListingOut)
async def pause_listing(
    listing_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.toggle_pause(db, listing_id, current_user)


@router.post("/listings/{listing_id}/photos", response_model=ListingOut)
async def upload_photos(
    listing_id: uuid.UUID,
    current_user: CurrentUser,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    return await service.add_photos(db, listing_id, current_user, files, storage)


@router.post("/listings/{listing_id}/upload-file", response_model=UploadFileOut)
async def upload_listing_file(
    listing_id: uuid.UUID,
    current_user: CurrentUser,
    field: UploadFileField = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    url = await service.upload_file(db, listing_id, current_user, field, file, storage)
    return UploadFileOut(url=url)


@router.delete("/listings/{listing_id}/photos/{photo_id}", status_code=204)
async def delete_listing_photo(
    listing_id: uuid.UUID,
    photo_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    await service.delete_photo(db, listing_id, photo_id, current_user, storage)


@router.post("/admin/listings/{listing_id}/approve", response_model=ListingOut)
async def approve_listing(
    listing_id: uuid.UUID,
    admin: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: AsyncSession = Depends(get_db),
):
    listing = await service.approve(db, listing_id)
    await admin_service.log_action(db, admin, AuditAction.listing_approve, "listing", listing_id)
    return listing


@router.post("/admin/listings/{listing_id}/reject", response_model=ListingOut)
async def reject_listing(
    listing_id: uuid.UUID,
    payload: RejectRequest,
    admin: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: AsyncSession = Depends(get_db),
):
    listing = await service.reject(db, listing_id, payload.reason)
    await admin_service.log_action(
        db, admin, AuditAction.listing_reject, "listing", listing_id, payload.reason
    )
    return listing
