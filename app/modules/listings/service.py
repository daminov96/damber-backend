import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.storage import StoragePort
from app.modules.listings.models import Listing, ListingPhoto, ListingType, Region, SortOption
from app.modules.listings.schemas import ListingCreateRequest, ListingUpdateRequest
from app.modules.users.models import User, UserRole

MAX_PHOTOS_PER_LISTING = 10
MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_PHOTO_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


async def _get_or_404(db: AsyncSession, listing_id: uuid.UUID) -> Listing:
    stmt = select(Listing).options(selectinload(Listing.photos)).where(Listing.id == listing_id)
    result = await db.execute(stmt)
    listing = result.scalar_one_or_none()
    if not listing:
        raise NotFoundError("Listing topilmadi")
    return listing


def _check_owner_or_admin(listing: Listing, user: User) -> None:
    if listing.owner_id != user.id and user.role != UserRole.ADMIN:
        raise ForbiddenError("Bu amal uchun ruxsatingiz yo'q")


def _visible_to(listing: Listing, user: User | None) -> bool:
    if listing.verified and not listing.paused:
        return True
    return bool(user and (user.id == listing.owner_id or user.role == UserRole.ADMIN))


async def search(
    db: AsyncSession,
    *,
    type: ListingType | None,
    region: Region | None,
    min_price: float | None,
    max_price: float | None,
    amenities: list[str] | None,
    guests: int | None,
    sort: SortOption,
    page: int,
    page_size: int,
) -> tuple[list[Listing], int]:
    conditions = [Listing.verified.is_(True), Listing.paused.is_(False)]
    if type is not None:
        conditions.append(Listing.type == type)
    if region is not None:
        conditions.append(Listing.region == region)
    if min_price is not None:
        conditions.append(Listing.weekday_price >= min_price)
    if max_price is not None:
        conditions.append(Listing.weekday_price <= max_price)
    if guests is not None:
        conditions.append(Listing.capacity >= guests)
    if amenities:
        conditions.append(Listing.amenities.contains(amenities))

    count_stmt = select(func.count()).select_from(Listing).where(*conditions)
    total = (await db.execute(count_stmt)).scalar_one()

    order_map = {
        SortOption.price_asc: [Listing.weekday_price.asc()],
        SortOption.price_desc: [Listing.weekday_price.desc()],
        SortOption.rating: [Listing.rating.desc()],
        SortOption.newest: [Listing.created_at.desc()],
        SortOption.hot: [Listing.is_hot.desc(), Listing.created_at.desc()],
        SortOption.most_saved: [Listing.saves.desc()],
    }

    stmt = (
        select(Listing)
        .options(selectinload(Listing.photos))
        .where(*conditions)
        .order_by(*order_map[sort])
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return items, total


async def get_by_id(db: AsyncSession, listing_id: uuid.UUID, current_user: User | None) -> Listing:
    listing = await _get_or_404(db, listing_id)
    if not _visible_to(listing, current_user):
        raise NotFoundError("Listing topilmadi")
    return listing


async def list_mine(db: AsyncSession, owner: User) -> list[Listing]:
    stmt = (
        select(Listing)
        .options(selectinload(Listing.photos))
        .where(Listing.owner_id == owner.id)
        .order_by(Listing.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create(db: AsyncSession, owner: User, payload: ListingCreateRequest) -> Listing:
    listing = Listing(**payload.model_dump(), owner_id=owner.id, verified=False, paused=False)
    db.add(listing)
    await db.commit()
    await db.refresh(listing, attribute_names=["photos"])
    return listing


async def update(
    db: AsyncSession, listing_id: uuid.UUID, current_user: User, payload: ListingUpdateRequest
) -> Listing:
    listing = await _get_or_404(db, listing_id)
    _check_owner_or_admin(listing, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(listing, field, value)
    await db.commit()
    await db.refresh(listing, attribute_names=["photos"])
    return listing


async def delete(
    db: AsyncSession, listing_id: uuid.UUID, current_user: User, storage: StoragePort
) -> None:
    listing = await _get_or_404(db, listing_id)
    _check_owner_or_admin(listing, current_user)
    for photo in listing.photos:
        try:
            await storage.delete(photo.url)
        except OSError:
            pass
    await db.delete(listing)
    await db.commit()


async def toggle_pause(db: AsyncSession, listing_id: uuid.UUID, current_user: User) -> Listing:
    listing = await _get_or_404(db, listing_id)
    if listing.owner_id != current_user.id:
        raise ForbiddenError("Faqat egasi to'xtata oladi")
    listing.paused = not listing.paused
    await db.commit()
    await db.refresh(listing, attribute_names=["photos"])
    return listing


async def approve(db: AsyncSession, listing_id: uuid.UUID) -> Listing:
    listing = await _get_or_404(db, listing_id)
    listing.verified = True
    await db.commit()
    await db.refresh(listing, attribute_names=["photos"])
    return listing


def _validate_photo_file(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_PHOTO_CONTENT_TYPES:
        raise HTTPException(400, detail="Faqat jpg/png/webp formatlariga ruxsat berilgan")


async def add_photos(
    db: AsyncSession,
    listing_id: uuid.UUID,
    current_user: User,
    files: list[UploadFile],
    storage: StoragePort,
) -> Listing:
    listing = await _get_or_404(db, listing_id)
    _check_owner_or_admin(listing, current_user)
    if len(listing.photos) + len(files) > MAX_PHOTOS_PER_LISTING:
        raise HTTPException(400, detail="Bitta listingga maksimal 10 ta rasm yuklash mumkin")

    next_position = len(listing.photos)
    new_photos = []
    for file in files:
        _validate_photo_file(file)
        content = await file.read()
        if len(content) > MAX_PHOTO_SIZE_BYTES:
            raise HTTPException(400, detail="Fayl hajmi 5MB dan oshmasligi kerak")
        await file.seek(0)
        url = await storage.save(file, subdir=str(listing_id))
        new_photos.append(ListingPhoto(listing_id=listing_id, url=url, position=next_position))
        next_position += 1

    db.add_all(new_photos)
    await db.commit()
    await db.refresh(listing, attribute_names=["photos"])
    return listing


async def delete_photo(
    db: AsyncSession,
    listing_id: uuid.UUID,
    photo_id: uuid.UUID,
    current_user: User,
    storage: StoragePort,
) -> None:
    listing = await _get_or_404(db, listing_id)
    _check_owner_or_admin(listing, current_user)
    photo = next((p for p in listing.photos if p.id == photo_id), None)
    if not photo:
        raise NotFoundError("Rasm topilmadi")
    await storage.delete(photo.url)
    await db.delete(photo)
    await db.commit()
