import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.storage import StoragePort
from app.modules.guides.models import Guide
from app.modules.listings.models import Region
from app.modules.operators.models import TourOperator
from app.modules.reviews.models import Review
from app.modules.tours.models import Tour, TourBooking, TourBookingStatus, TourPhoto, TourSortOption
from app.modules.tours.schemas import TourBookingCreateRequest, TourCreateRequest, TourUpdateRequest
from app.modules.users.models import User, UserRole

MAX_PHOTOS_PER_TOUR = 10
MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_PHOTO_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


async def _get_or_404(db: AsyncSession, tour_id: uuid.UUID) -> Tour:
    stmt = select(Tour).options(selectinload(Tour.photos)).where(Tour.id == tour_id)
    tour = (await db.execute(stmt)).scalar_one_or_none()
    if not tour:
        raise NotFoundError("Tur topilmadi")
    return tour


async def _get_operator(db: AsyncSession, operator_id: uuid.UUID) -> TourOperator:
    stmt = select(TourOperator).where(TourOperator.id == operator_id)
    operator = (await db.execute(stmt)).scalar_one_or_none()
    if not operator:
        raise NotFoundError("Operator topilmadi")
    return operator


async def _get_guide(db: AsyncSession, guide_id: uuid.UUID) -> Guide:
    stmt = select(Guide).where(Guide.id == guide_id)
    guide = (await db.execute(stmt)).scalar_one_or_none()
    if not guide:
        raise NotFoundError("Gid topilmadi")
    return guide


def _check_owner_or_admin(tour: Tour, user: User) -> None:
    if tour.owner_id != user.id and user.role != UserRole.ADMIN:
        raise ForbiddenError("Bu amal uchun ruxsatingiz yo'q")


def _visible_to(tour: Tour, user: User | None) -> bool:
    if not tour.pending:
        return True
    return bool(user and (user.id == tour.owner_id or user.role == UserRole.ADMIN))


async def search(
    db: AsyncSession,
    *,
    query: str | None,
    region: Region | None,
    category: str | None,
    nights_min: int | None,
    nights_max: int | None,
    max_price: float | None,
    discount_only: bool,
    sort: TourSortOption,
    page: int,
    page_size: int,
) -> tuple[list[Tour], int]:
    conditions = [Tour.pending.is_(False)]
    if query:
        conditions.append(Tour.name.ilike(f"%{query}%"))
    if region is not None:
        conditions.append(Tour.region == region)
    if category is not None:
        conditions.append(Tour.category == category)
    if nights_min is not None:
        conditions.append(Tour.nights >= nights_min)
    if nights_max is not None:
        conditions.append(Tour.nights <= nights_max)
    if max_price is not None:
        conditions.append(Tour.price <= max_price)
    if discount_only:
        conditions.append(Tour.old_price > 0)
        conditions.append(Tour.old_price > Tour.price)

    count_stmt = select(func.count()).select_from(Tour).where(*conditions)
    total = (await db.execute(count_stmt)).scalar_one()

    order_map = {
        TourSortOption.rating: [Tour.rating.desc()],
        TourSortOption.newest: [Tour.created_at.desc()],
        TourSortOption.price_asc: [Tour.price.asc()],
        TourSortOption.price_desc: [Tour.price.desc()],
    }

    stmt = (
        select(Tour)
        .options(selectinload(Tour.photos))
        .where(*conditions)
        .order_by(*order_map[sort])
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def get_by_id(db: AsyncSession, tour_id: uuid.UUID, current_user: User | None) -> Tour:
    tour = await _get_or_404(db, tour_id)
    if not _visible_to(tour, current_user):
        raise NotFoundError("Tur topilmadi")
    return tour


async def list_mine(db: AsyncSession, owner: User) -> list[Tour]:
    stmt = (
        select(Tour)
        .options(selectinload(Tour.photos))
        .where(Tour.owner_id == owner.id)
        .order_by(Tour.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create(db: AsyncSession, current_user: User, payload: TourCreateRequest) -> Tour:
    if payload.operator_id is not None:
        operator = await _get_operator(db, payload.operator_id)
        if operator.owner_id != current_user.id:
            raise ForbiddenError("Faqat o'z operator profilingizga tur qo'sha olasiz")
        owner_id = operator.owner_id
    else:
        guide = await _get_guide(db, payload.guide_id)
        if guide.owner_id != current_user.id:
            raise ForbiddenError("Faqat o'z gid profilingizga tur qo'sha olasiz")
        owner_id = guide.owner_id

    tour = Tour(
        **payload.model_dump(exclude={"operator_id", "guide_id"}),
        operator_id=payload.operator_id,
        guide_id=payload.guide_id,
        owner_id=owner_id,
        pending=True,
    )
    db.add(tour)
    await db.commit()
    await db.refresh(tour, attribute_names=["photos", "operator", "guide"])
    return tour


async def update(
    db: AsyncSession, tour_id: uuid.UUID, current_user: User, payload: TourUpdateRequest
) -> Tour:
    tour = await _get_or_404(db, tour_id)
    _check_owner_or_admin(tour, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tour, field, value)
    # Tahrirlash — rad etilgan turni qayta ko'rib chiqishga avtomatik yuboradi
    if tour.rejected:
        tour.rejected = False
        tour.reject_reason = None
    await db.commit()
    await db.refresh(tour, attribute_names=["photos", "operator", "guide"])
    return tour


async def delete(db: AsyncSession, tour_id: uuid.UUID, current_user: User) -> None:
    tour = await _get_or_404(db, tour_id)
    _check_owner_or_admin(tour, current_user)
    await db.delete(tour)
    await db.commit()


async def approve(db: AsyncSession, tour_id: uuid.UUID) -> Tour:
    tour = await _get_or_404(db, tour_id)
    tour.pending = False
    await db.commit()
    await db.refresh(tour, attribute_names=["photos", "operator", "guide"])
    return tour


async def reject(db: AsyncSession, tour_id: uuid.UUID, reason: str) -> Tour:
    tour = await _get_or_404(db, tour_id)
    if not tour.pending:
        raise ConflictError(
            "Tasdiqlangan turni rad etib bo'lmaydi — avval to'xtatib qo'ying"
        )
    tour.rejected = True
    tour.reject_reason = reason
    await db.commit()
    await db.refresh(tour, attribute_names=["photos", "operator", "guide"])
    return tour


async def list_pending(db: AsyncSession, page: int, page_size: int) -> tuple[list[Tour], int]:
    conditions = [Tour.pending.is_(True), Tour.rejected.is_(False)]

    count_stmt = select(func.count()).select_from(Tour).where(*conditions)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Tour)
        .options(selectinload(Tour.photos))
        .where(*conditions)
        .order_by(Tour.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


def _validate_photo_file(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_PHOTO_CONTENT_TYPES:
        raise HTTPException(400, detail="Faqat jpg/png/webp formatlariga ruxsat berilgan")


async def add_photos(
    db: AsyncSession,
    tour_id: uuid.UUID,
    current_user: User,
    files: list[UploadFile],
    storage: StoragePort,
) -> Tour:
    tour = await _get_or_404(db, tour_id)
    _check_owner_or_admin(tour, current_user)
    if len(tour.photos) + len(files) > MAX_PHOTOS_PER_TOUR:
        raise HTTPException(400, detail="Bitta turga maksimal 10 ta rasm yuklash mumkin")

    next_position = len(tour.photos)
    new_photos = []
    for file in files:
        _validate_photo_file(file)
        content = await file.read()
        if len(content) > MAX_PHOTO_SIZE_BYTES:
            raise HTTPException(400, detail="Fayl hajmi 5MB dan oshmasligi kerak")
        await file.seek(0)
        url = await storage.save(file, subdir=str(tour_id))
        photo = TourPhoto(tour_id=tour_id, url=url, position=next_position)
        new_photos.append(photo)
        next_position += 1

    db.add_all(new_photos)
    await db.commit()
    await db.refresh(tour, attribute_names=["photos", "operator", "guide"])
    return tour


async def delete_photo(
    db: AsyncSession,
    tour_id: uuid.UUID,
    photo_id: uuid.UUID,
    current_user: User,
    storage: StoragePort,
) -> None:
    tour = await _get_or_404(db, tour_id)
    _check_owner_or_admin(tour, current_user)
    photo = next((p for p in tour.photos if p.id == photo_id), None)
    if not photo:
        raise NotFoundError("Rasm topilmadi")
    await storage.delete(photo.url)
    await db.delete(photo)
    await db.commit()


async def recompute_rating(db: AsyncSession, tour_id: uuid.UUID) -> None:
    stmt = select(func.avg(Review.stars), func.count(Review.id)).where(Review.tour_id == tour_id)
    avg, count = (await db.execute(stmt)).one()
    tour = await _get_or_404(db, tour_id)
    tour.rating = round(float(avg), 2) if avg is not None else 0.0
    tour.rating_count = count
    await db.commit()


# ── Tur bron so'rovlari (to'lovsiz lead-capture) ──


async def _get_booking_or_404(db: AsyncSession, booking_id: uuid.UUID) -> TourBooking:
    stmt = select(TourBooking).where(TourBooking.id == booking_id)
    booking = (await db.execute(stmt)).scalar_one_or_none()
    if not booking:
        raise NotFoundError("Bron so'rovi topilmadi")
    return booking


async def _check_tour_host(db: AsyncSession, tour_id: uuid.UUID, user: User) -> Tour:
    tour = await _get_or_404(db, tour_id)
    _check_owner_or_admin(tour, user)
    return tour


async def create_booking(
    db: AsyncSession, client: User, tour_id: uuid.UUID, payload: TourBookingCreateRequest
) -> TourBooking:
    tour = await _get_or_404(db, tour_id)
    booking = TourBooking(
        tour_id=tour.id,
        client_id=client.id,
        name=payload.name,
        phone=payload.phone,
        people=payload.people,
        total_estimate=float(tour.price) * payload.people,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking


async def list_tour_bookings(
    db: AsyncSession, tour_id: uuid.UUID, host: User, page: int, page_size: int
) -> tuple[list[TourBooking], int]:
    await _check_tour_host(db, tour_id, host)

    count_stmt = select(func.count()).select_from(TourBooking).where(TourBooking.tour_id == tour_id)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(TourBooking)
        .where(TourBooking.tour_id == tour_id)
        .order_by(TourBooking.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def list_my_bookings(
    db: AsyncSession, client: User, page: int, page_size: int
) -> tuple[list[TourBooking], int]:
    count_stmt = (
        select(func.count()).select_from(TourBooking).where(TourBooking.client_id == client.id)
    )
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(TourBooking)
        .where(TourBooking.client_id == client.id)
        .order_by(TourBooking.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def _transition_booking(
    db: AsyncSession, booking_id: uuid.UUID, host: User, new_status: TourBookingStatus
) -> TourBooking:
    booking = await _get_booking_or_404(db, booking_id)
    await _check_tour_host(db, booking.tour_id, host)
    if booking.status != TourBookingStatus.pending:
        raise ConflictError("Bron holati bunga mos emas")
    booking.status = new_status
    await db.commit()
    await db.refresh(booking)
    return booking


async def confirm_booking(db: AsyncSession, booking_id: uuid.UUID, host: User) -> TourBooking:
    return await _transition_booking(db, booking_id, host, TourBookingStatus.confirmed)


async def reject_booking(db: AsyncSession, booking_id: uuid.UUID, host: User) -> TourBooking:
    return await _transition_booking(db, booking_id, host, TourBookingStatus.rejected)
