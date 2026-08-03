import uuid
from datetime import date

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.storage import StoragePort
from app.modules.listings.models import Region
from app.modules.operators.models import (
    OperatorSortOption,
    OperatorSpecTag,
    TourOperator,
    TourOperatorPhoto,
)
from app.modules.operators.schemas import OperatorCreateRequest, OperatorUpdateRequest
from app.modules.tours.models import Tour
from app.modules.users.models import User, UserRole

MAX_PHOTOS_PER_OPERATOR = 10
MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_PHOTO_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


async def _get_or_404(db: AsyncSession, operator_id: uuid.UUID) -> TourOperator:
    stmt = (
        select(TourOperator)
        .options(selectinload(TourOperator.photos))
        .where(TourOperator.id == operator_id)
    )
    operator = (await db.execute(stmt)).scalar_one_or_none()
    if not operator:
        raise NotFoundError("Operator topilmadi")
    return operator


def _check_owner_or_admin(operator: TourOperator, user: User) -> None:
    if operator.owner_id != user.id and user.role != UserRole.ADMIN:
        raise ForbiddenError("Bu amal uchun ruxsatingiz yo'q")


async def search(
    db: AsyncSession,
    *,
    query: str | None,
    region: Region | None,
    spec_tag: OperatorSpecTag | None,
    min_rating: float | None,
    sort: OperatorSortOption,
    page: int,
    page_size: int,
) -> tuple[list[TourOperator], int]:
    conditions = []
    if query:
        conditions.append(TourOperator.name.ilike(f"%{query}%"))
    if region is not None:
        conditions.append(TourOperator.region == region)
    if spec_tag is not None:
        conditions.append(TourOperator.spec_tag == spec_tag)
    if min_rating is not None:
        conditions.append(TourOperator.rating >= min_rating)

    count_stmt = select(func.count()).select_from(TourOperator).where(*conditions)
    total = (await db.execute(count_stmt)).scalar_one()

    order_map = {
        OperatorSortOption.rating: [TourOperator.rating.desc()],
        OperatorSortOption.name: [TourOperator.name.asc()],
        OperatorSortOption.newest: [TourOperator.created_at.desc()],
    }

    stmt = (
        select(TourOperator)
        .options(selectinload(TourOperator.photos))
        .where(*conditions)
        .order_by(*order_map[sort])
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def get_by_id(db: AsyncSession, operator_id: uuid.UUID) -> TourOperator:
    return await _get_or_404(db, operator_id)


async def list_mine(db: AsyncSession, owner: User) -> list[TourOperator]:
    stmt = (
        select(TourOperator)
        .options(selectinload(TourOperator.photos))
        .where(TourOperator.owner_id == owner.id)
        .order_by(TourOperator.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create(db: AsyncSession, owner: User, payload: OperatorCreateRequest) -> TourOperator:
    founded = payload.founded or date.today().year
    license_issued = f"{founded}-yil, O'zbekiston Turizm va sport vazirligi tomonidan berilgan"

    operator = TourOperator(
        **payload.model_dump(exclude={"founded"}),
        founded=founded,
        license_issued=license_issued,
        owner_id=owner.id,
    )
    db.add(operator)
    await db.commit()
    await db.refresh(operator, attribute_names=["photos"])
    return operator


async def update(
    db: AsyncSession, operator_id: uuid.UUID, current_user: User, payload: OperatorUpdateRequest
) -> TourOperator:
    operator = await _get_or_404(db, operator_id)
    _check_owner_or_admin(operator, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(operator, field, value)
    await db.commit()
    await db.refresh(operator, attribute_names=["photos"])
    return operator


async def delete(db: AsyncSession, operator_id: uuid.UUID, current_user: User) -> None:
    operator = await _get_or_404(db, operator_id)
    _check_owner_or_admin(operator, current_user)
    has_tours = (
        await db.execute(select(Tour.id).where(Tour.operator_id == operator_id).limit(1))
    ).first()
    if has_tours:
        raise ConflictError("Bu operatorga tegishli turlar mavjud — avval ularni o'chiring")
    await db.delete(operator)
    await db.commit()


def _validate_photo_file(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_PHOTO_CONTENT_TYPES:
        raise HTTPException(400, detail="Faqat jpg/png/webp formatlariga ruxsat berilgan")


async def add_photos(
    db: AsyncSession,
    operator_id: uuid.UUID,
    current_user: User,
    files: list[UploadFile],
    storage: StoragePort,
) -> TourOperator:
    operator = await _get_or_404(db, operator_id)
    _check_owner_or_admin(operator, current_user)
    if len(operator.photos) + len(files) > MAX_PHOTOS_PER_OPERATOR:
        raise HTTPException(400, detail="Bitta operatorga maksimal 10 ta rasm yuklash mumkin")

    next_position = len(operator.photos)
    new_photos = []
    for file in files:
        _validate_photo_file(file)
        content = await file.read()
        if len(content) > MAX_PHOTO_SIZE_BYTES:
            raise HTTPException(400, detail="Fayl hajmi 5MB dan oshmasligi kerak")
        await file.seek(0)
        url = await storage.save(file, subdir=str(operator_id))
        photo = TourOperatorPhoto(operator_id=operator_id, url=url, position=next_position)
        new_photos.append(photo)
        next_position += 1

    db.add_all(new_photos)
    await db.commit()
    await db.refresh(operator, attribute_names=["photos"])
    return operator


async def delete_photo(
    db: AsyncSession,
    operator_id: uuid.UUID,
    photo_id: uuid.UUID,
    current_user: User,
    storage: StoragePort,
) -> None:
    operator = await _get_or_404(db, operator_id)
    _check_owner_or_admin(operator, current_user)
    photo = next((p for p in operator.photos if p.id == photo_id), None)
    if not photo:
        raise NotFoundError("Rasm topilmadi")
    await storage.delete(photo.url)
    await db.delete(photo)
    await db.commit()
