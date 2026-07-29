import uuid
from datetime import date

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.storage import StoragePort
from app.modules.listings.models import Listing, Region
from app.modules.rent_companies.models import RentCompany, RentCompanyPhoto, RentCompanySortOption
from app.modules.rent_companies.schemas import RentCompanyCreateRequest, RentCompanyUpdateRequest
from app.modules.users.models import User, UserRole

MAX_PHOTOS_PER_COMPANY = 10
MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_PHOTO_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


async def _get_or_404(db: AsyncSession, company_id: uuid.UUID) -> RentCompany:
    stmt = (
        select(RentCompany)
        .options(selectinload(RentCompany.photos))
        .where(RentCompany.id == company_id)
    )
    company = (await db.execute(stmt)).scalar_one_or_none()
    if not company:
        raise NotFoundError("Ijara kompaniyasi topilmadi")
    return company


def _check_owner_or_admin(company: RentCompany, user: User) -> None:
    if company.owner_id != user.id and user.role != UserRole.ADMIN:
        raise ForbiddenError("Bu amal uchun ruxsatingiz yo'q")


async def search(
    db: AsyncSession,
    *,
    query: str | None,
    region: Region | None,
    sort: RentCompanySortOption,
    page: int,
    page_size: int,
) -> tuple[list[RentCompany], int]:
    conditions = []
    if query:
        conditions.append(RentCompany.name.ilike(f"%{query}%"))
    if region is not None:
        conditions.append(RentCompany.region == region)

    count_stmt = select(func.count()).select_from(RentCompany).where(*conditions)
    total = (await db.execute(count_stmt)).scalar_one()

    order_map = {
        RentCompanySortOption.rating: [RentCompany.rating.desc()],
        RentCompanySortOption.name: [RentCompany.name.asc()],
        RentCompanySortOption.newest: [RentCompany.created_at.desc()],
    }

    stmt = (
        select(RentCompany)
        .options(selectinload(RentCompany.photos))
        .where(*conditions)
        .order_by(*order_map[sort])
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def get_by_id(db: AsyncSession, company_id: uuid.UUID) -> RentCompany:
    return await _get_or_404(db, company_id)


async def list_mine(db: AsyncSession, owner: User) -> list[RentCompany]:
    stmt = (
        select(RentCompany)
        .options(selectinload(RentCompany.photos))
        .where(RentCompany.owner_id == owner.id)
        .order_by(RentCompany.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create(db: AsyncSession, owner: User, payload: RentCompanyCreateRequest) -> RentCompany:
    founded = payload.founded or date.today().year
    company = RentCompany(
        **payload.model_dump(exclude={"founded"}),
        founded=founded,
        owner_id=owner.id,
    )
    db.add(company)
    await db.commit()
    await db.refresh(company, attribute_names=["photos"])
    return company


async def update(
    db: AsyncSession, company_id: uuid.UUID, current_user: User, payload: RentCompanyUpdateRequest
) -> RentCompany:
    company = await _get_or_404(db, company_id)
    _check_owner_or_admin(company, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    await db.commit()
    await db.refresh(company, attribute_names=["photos"])
    return company


async def delete(db: AsyncSession, company_id: uuid.UUID, current_user: User) -> None:
    """Bog'langan RentCar listinglar o'chirilmaydi — `company_id` NULL bo'ladi
    (DB darajasidagi `ON DELETE SET NULL`, bog'lanish ixtiyoriy bo'lgani uchun
    Operators/Tours'dagidek oldindan tekshiruv shart emas)."""
    company = await _get_or_404(db, company_id)
    _check_owner_or_admin(company, current_user)
    await db.delete(company)
    await db.commit()


def _validate_photo_file(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_PHOTO_CONTENT_TYPES:
        raise HTTPException(400, detail="Faqat jpg/png/webp formatlariga ruxsat berilgan")


async def add_photos(
    db: AsyncSession,
    company_id: uuid.UUID,
    current_user: User,
    files: list[UploadFile],
    storage: StoragePort,
) -> RentCompany:
    company = await _get_or_404(db, company_id)
    _check_owner_or_admin(company, current_user)
    if len(company.photos) + len(files) > MAX_PHOTOS_PER_COMPANY:
        raise HTTPException(400, detail="Bitta kompaniyaga maksimal 10 ta rasm yuklash mumkin")

    next_position = len(company.photos)
    new_photos = []
    for file in files:
        _validate_photo_file(file)
        content = await file.read()
        if len(content) > MAX_PHOTO_SIZE_BYTES:
            raise HTTPException(400, detail="Fayl hajmi 5MB dan oshmasligi kerak")
        await file.seek(0)
        url = await storage.save(file, subdir=str(company_id))
        photo = RentCompanyPhoto(company_id=company_id, url=url, position=next_position)
        new_photos.append(photo)
        next_position += 1

    db.add_all(new_photos)
    await db.commit()
    await db.refresh(company, attribute_names=["photos"])
    return company


async def delete_photo(
    db: AsyncSession,
    company_id: uuid.UUID,
    photo_id: uuid.UUID,
    current_user: User,
    storage: StoragePort,
) -> None:
    company = await _get_or_404(db, company_id)
    _check_owner_or_admin(company, current_user)
    photo = next((p for p in company.photos if p.id == photo_id), None)
    if not photo:
        raise NotFoundError("Rasm topilmadi")
    await storage.delete(photo.url)
    await db.delete(photo)
    await db.commit()


async def list_company_listings(
    db: AsyncSession, company_id: uuid.UUID, page: int, page_size: int
) -> tuple[list[Listing], int]:
    conditions = [
        Listing.company_id == company_id,
        Listing.verified.is_(True),
        Listing.paused.is_(False),
    ]
    count_stmt = select(func.count()).select_from(Listing).where(*conditions)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Listing)
        .options(selectinload(Listing.photos))
        .where(*conditions)
        .order_by(Listing.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total
