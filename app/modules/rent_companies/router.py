import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_role
from app.core.storage import StoragePort, get_storage
from app.modules.listings.models import Region
from app.modules.listings.schemas import ListingListOut
from app.modules.rent_companies import service
from app.modules.rent_companies.models import RentCompanySortOption
from app.modules.rent_companies.schemas import (
    RentCompanyCreateRequest,
    RentCompanyListOut,
    RentCompanyOut,
    RentCompanyUpdateRequest,
)
from app.modules.users.models import User, UserRole

router = APIRouter(prefix="/api/v1", tags=["rent-companies"])


@router.get("/rent-companies", response_model=RentCompanyListOut)
async def list_rent_companies(
    db: AsyncSession = Depends(get_db),
    query: str | None = Query(None),
    region: Region | None = Query(None),
    sort: RentCompanySortOption = Query(RentCompanySortOption.rating),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.search(
        db, query=query, region=region, sort=sort, page=page, page_size=page_size
    )
    return RentCompanyListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/rent-companies/mine", response_model=list[RentCompanyOut])
async def my_rent_companies(
    current_user: Annotated[User, Depends(require_role(UserRole.B2B, UserRole.ADMIN))],
    db: AsyncSession = Depends(get_db),
):
    return await service.list_mine(db, current_user)


@router.get("/rent-companies/{company_id}", response_model=RentCompanyOut)
async def get_rent_company(company_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await service.get_by_id(db, company_id)


@router.get("/rent-companies/{company_id}/listings", response_model=ListingListOut)
async def list_rent_company_listings(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.list_company_listings(db, company_id, page, page_size)
    return ListingListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/rent-companies", response_model=RentCompanyOut, status_code=201)
async def create_rent_company(
    payload: RentCompanyCreateRequest,
    current_user: Annotated[User, Depends(require_role(UserRole.B2B))],
    db: AsyncSession = Depends(get_db),
):
    return await service.create(db, current_user, payload)


@router.patch("/rent-companies/{company_id}", response_model=RentCompanyOut)
async def update_rent_company(
    company_id: uuid.UUID,
    payload: RentCompanyUpdateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.update(db, company_id, current_user, payload)


@router.delete("/rent-companies/{company_id}", status_code=204)
async def delete_rent_company(
    company_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    await service.delete(db, company_id, current_user)


@router.post("/rent-companies/{company_id}/photos", response_model=RentCompanyOut)
async def upload_rent_company_photos(
    company_id: uuid.UUID,
    current_user: CurrentUser,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    return await service.add_photos(db, company_id, current_user, files, storage)


@router.delete("/rent-companies/{company_id}/photos/{photo_id}", status_code=204)
async def delete_rent_company_photo(
    company_id: uuid.UUID,
    photo_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    await service.delete_photo(db, company_id, photo_id, current_user, storage)
