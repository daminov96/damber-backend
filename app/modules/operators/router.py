import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_role
from app.core.storage import StoragePort, get_storage
from app.modules.listings.models import Region
from app.modules.operators import service
from app.modules.operators.models import OperatorSortOption, OperatorSpecTag
from app.modules.operators.schemas import (
    OperatorCreateRequest,
    OperatorUpdateRequest,
    TourOperatorListOut,
    TourOperatorOut,
)
from app.modules.users.models import User, UserRole

router = APIRouter(prefix="/api/v1", tags=["operators"])


@router.get("/operators", response_model=TourOperatorListOut)
async def list_operators(
    db: AsyncSession = Depends(get_db),
    query: str | None = Query(None),
    region: Region | None = Query(None),
    spec_tag: OperatorSpecTag | None = Query(None),
    sort: OperatorSortOption = Query(OperatorSortOption.rating),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.search(
        db, query=query, region=region, spec_tag=spec_tag, sort=sort, page=page, page_size=page_size
    )
    return TourOperatorListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/operators/mine", response_model=list[TourOperatorOut])
async def my_operators(
    current_user: Annotated[User, Depends(require_role(UserRole.B2B, UserRole.ADMIN))],
    db: AsyncSession = Depends(get_db),
):
    return await service.list_mine(db, current_user)


@router.get("/operators/{operator_id}", response_model=TourOperatorOut)
async def get_operator(operator_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await service.get_by_id(db, operator_id)


@router.post("/operators", response_model=TourOperatorOut, status_code=201)
async def create_operator(
    payload: OperatorCreateRequest,
    current_user: Annotated[User, Depends(require_role(UserRole.B2B))],
    db: AsyncSession = Depends(get_db),
):
    return await service.create(db, current_user, payload)


@router.patch("/operators/{operator_id}", response_model=TourOperatorOut)
async def update_operator(
    operator_id: uuid.UUID,
    payload: OperatorUpdateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.update(db, operator_id, current_user, payload)


@router.delete("/operators/{operator_id}", status_code=204)
async def delete_operator(
    operator_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    await service.delete(db, operator_id, current_user)


@router.post("/operators/{operator_id}/photos", response_model=TourOperatorOut)
async def upload_operator_photos(
    operator_id: uuid.UUID,
    current_user: CurrentUser,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    return await service.add_photos(db, operator_id, current_user, files, storage)


@router.delete("/operators/{operator_id}/photos/{photo_id}", status_code=204)
async def delete_operator_photo(
    operator_id: uuid.UUID,
    photo_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    await service.delete_photo(db, operator_id, photo_id, current_user, storage)
