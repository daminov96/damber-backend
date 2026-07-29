import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_role
from app.core.storage import StoragePort, get_storage
from app.modules.guides import service
from app.modules.guides.models import GuideSortOption, GuideType
from app.modules.guides.schemas import (
    GuideCreateRequest,
    GuideListOut,
    GuideOut,
    GuideUpdateRequest,
)
from app.modules.listings.models import Region
from app.modules.users.models import User, UserRole

router = APIRouter(prefix="/api/v1", tags=["guides"])


@router.get("/guides", response_model=GuideListOut)
async def list_guides(
    db: AsyncSession = Depends(get_db),
    query: str | None = Query(None),
    region: Region | None = Query(None),
    guide_type: GuideType | None = Query(None),
    sort: GuideSortOption = Query(GuideSortOption.rating),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.search(
        db,
        query=query,
        region=region,
        guide_type=guide_type,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return GuideListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/guides/mine", response_model=list[GuideOut])
async def my_guides(
    current_user: Annotated[User, Depends(require_role(UserRole.B2B, UserRole.ADMIN))],
    db: AsyncSession = Depends(get_db),
):
    return await service.list_mine(db, current_user)


@router.get("/guides/{guide_id}", response_model=GuideOut)
async def get_guide(guide_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await service.get_by_id(db, guide_id)


@router.post("/guides", response_model=GuideOut, status_code=201)
async def create_guide(
    payload: GuideCreateRequest,
    current_user: Annotated[User, Depends(require_role(UserRole.B2B))],
    db: AsyncSession = Depends(get_db),
):
    return await service.create(db, current_user, payload)


@router.patch("/guides/{guide_id}", response_model=GuideOut)
async def update_guide(
    guide_id: uuid.UUID,
    payload: GuideUpdateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.update(db, guide_id, current_user, payload)


@router.delete("/guides/{guide_id}", status_code=204)
async def delete_guide(
    guide_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    await service.delete(db, guide_id, current_user)


@router.post("/guides/{guide_id}/photos", response_model=GuideOut)
async def upload_guide_photos(
    guide_id: uuid.UUID,
    current_user: CurrentUser,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    return await service.add_photos(db, guide_id, current_user, files, storage)


@router.delete("/guides/{guide_id}/photos/{photo_id}", status_code=204)
async def delete_guide_photo(
    guide_id: uuid.UUID,
    photo_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    await service.delete_photo(db, guide_id, photo_id, current_user, storage)
