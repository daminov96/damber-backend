import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.storage import StoragePort
from app.modules.guides.models import Guide, GuidePhoto, GuideSortOption, GuideType
from app.modules.guides.schemas import GuideCreateRequest, GuideUpdateRequest
from app.modules.listings.models import Region
from app.modules.tours.models import Tour
from app.modules.users.models import User, UserRole

MAX_PHOTOS_PER_GUIDE = 10
MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_PHOTO_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


async def _get_or_404(db: AsyncSession, guide_id: uuid.UUID) -> Guide:
    stmt = select(Guide).options(selectinload(Guide.photos)).where(Guide.id == guide_id)
    guide = (await db.execute(stmt)).scalar_one_or_none()
    if not guide:
        raise NotFoundError("Gid topilmadi")
    return guide


def _check_owner_or_admin(guide: Guide, user: User) -> None:
    if guide.owner_id != user.id and user.role != UserRole.ADMIN:
        raise ForbiddenError("Bu amal uchun ruxsatingiz yo'q")


async def search(
    db: AsyncSession,
    *,
    query: str | None,
    region: Region | None,
    guide_type: GuideType | None,
    sort: GuideSortOption,
    page: int,
    page_size: int,
) -> tuple[list[Guide], int]:
    conditions = []
    if query:
        conditions.append(Guide.name.ilike(f"%{query}%"))
    if region is not None:
        conditions.append(Guide.region == region)
    if guide_type is not None:
        conditions.append(Guide.guide_type == guide_type)

    count_stmt = select(func.count()).select_from(Guide).where(*conditions)
    total = (await db.execute(count_stmt)).scalar_one()

    order_map = {
        GuideSortOption.rating: [Guide.rating.desc()],
        GuideSortOption.name: [Guide.name.asc()],
        GuideSortOption.newest: [Guide.created_at.desc()],
    }

    stmt = (
        select(Guide)
        .options(selectinload(Guide.photos))
        .where(*conditions)
        .order_by(*order_map[sort])
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def get_by_id(db: AsyncSession, guide_id: uuid.UUID) -> Guide:
    return await _get_or_404(db, guide_id)


async def list_mine(db: AsyncSession, owner: User) -> list[Guide]:
    stmt = (
        select(Guide)
        .options(selectinload(Guide.photos))
        .where(Guide.owner_id == owner.id)
        .order_by(Guide.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create(db: AsyncSession, owner: User, payload: GuideCreateRequest) -> Guide:
    guide = Guide(
        **payload.model_dump(),
        owner_id=owner.id,
        certified=payload.license_doc_name is not None,
    )
    db.add(guide)
    await db.commit()
    await db.refresh(guide, attribute_names=["photos"])
    return guide


async def update(
    db: AsyncSession, guide_id: uuid.UUID, current_user: User, payload: GuideUpdateRequest
) -> Guide:
    guide = await _get_or_404(db, guide_id)
    _check_owner_or_admin(guide, current_user)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(guide, field, value)
    if "license_doc_name" in changes:
        guide.certified = guide.license_doc_name is not None
    await db.commit()
    await db.refresh(guide, attribute_names=["photos"])
    return guide


async def delete(db: AsyncSession, guide_id: uuid.UUID, current_user: User) -> None:
    guide = await _get_or_404(db, guide_id)
    _check_owner_or_admin(guide, current_user)
    has_tours = (
        await db.execute(select(Tour.id).where(Tour.guide_id == guide_id).limit(1))
    ).first()
    if has_tours:
        raise ConflictError("Bu gidga tegishli turlar mavjud — avval ularni o'chiring")
    await db.delete(guide)
    await db.commit()


def _validate_photo_file(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_PHOTO_CONTENT_TYPES:
        raise HTTPException(400, detail="Faqat jpg/png/webp formatlariga ruxsat berilgan")


async def add_photos(
    db: AsyncSession,
    guide_id: uuid.UUID,
    current_user: User,
    files: list[UploadFile],
    storage: StoragePort,
) -> Guide:
    guide = await _get_or_404(db, guide_id)
    _check_owner_or_admin(guide, current_user)
    if len(guide.photos) + len(files) > MAX_PHOTOS_PER_GUIDE:
        raise HTTPException(400, detail="Bitta gidga maksimal 10 ta rasm yuklash mumkin")

    next_position = len(guide.photos)
    new_photos = []
    for file in files:
        _validate_photo_file(file)
        content = await file.read()
        if len(content) > MAX_PHOTO_SIZE_BYTES:
            raise HTTPException(400, detail="Fayl hajmi 5MB dan oshmasligi kerak")
        await file.seek(0)
        url = await storage.save(file, subdir=str(guide_id))
        photo = GuidePhoto(guide_id=guide_id, url=url, position=next_position)
        new_photos.append(photo)
        next_position += 1

    db.add_all(new_photos)
    await db.commit()
    await db.refresh(guide, attribute_names=["photos"])
    return guide


async def delete_photo(
    db: AsyncSession,
    guide_id: uuid.UUID,
    photo_id: uuid.UUID,
    current_user: User,
    storage: StoragePort,
) -> None:
    guide = await _get_or_404(db, guide_id)
    _check_owner_or_admin(guide, current_user)
    photo = next((p for p in guide.photos if p.id == photo_id), None)
    if not photo:
        raise NotFoundError("Rasm topilmadi")
    await storage.delete(photo.url)
    await db.delete(photo)
    await db.commit()
