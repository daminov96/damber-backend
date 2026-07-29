import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.modules.bookings.models import Booking, BookingStatus
from app.modules.listings import service as listings_service
from app.modules.reviews.models import Review
from app.modules.reviews.schemas import ReviewCreateRequest, ReviewUpdateRequest
from app.modules.tours import service as tours_service
from app.modules.users.models import User, UserRole


async def _get_or_404(db: AsyncSession, review_id: uuid.UUID) -> Review:
    stmt = select(Review).where(Review.id == review_id)
    review = (await db.execute(stmt)).scalar_one_or_none()
    if not review:
        raise NotFoundError("Sharh topilmadi")
    return review


async def _get_booking_or_404(db: AsyncSession, booking_id: uuid.UUID) -> Booking:
    stmt = select(Booking).where(Booking.id == booking_id)
    booking = (await db.execute(stmt)).scalar_one_or_none()
    if not booking:
        raise NotFoundError("Bron topilmadi")
    return booking


async def create(db: AsyncSession, client: User, payload: ReviewCreateRequest) -> Review:
    if payload.listing_id is not None:
        booking = await _get_booking_or_404(db, payload.booking_id)
        if booking.client_id != client.id:
            raise ForbiddenError("Bu bron sizga tegishli emas")
        if booking.listing_id != payload.listing_id:
            raise HTTPException(400, detail="Bron boshqa listingga tegishli")
        if booking.status != BookingStatus.completed:
            raise ConflictError("Faqat yakunlangan bron uchun sharh qoldirish mumkin")
        already_reviewed = (
            await db.execute(select(Review.id).where(Review.booking_id == payload.booking_id))
        ).scalar_one_or_none()
        if already_reviewed:
            raise ConflictError("Bu bron allaqachon baholangan")
        verified = True
    else:
        already_reviewed = (
            await db.execute(
                select(Review.id).where(
                    Review.client_id == client.id, Review.tour_id == payload.tour_id
                )
            )
        ).scalar_one_or_none()
        if already_reviewed:
            raise ConflictError("Siz bu turga allaqachon sharh qoldirgansiz")
        verified = False

    review = Review(**payload.model_dump(), client_id=client.id, verified=verified)
    db.add(review)
    await db.commit()

    if payload.listing_id is not None:
        await listings_service.recompute_rating(db, payload.listing_id)
    else:
        await tours_service.recompute_rating(db, payload.tour_id)

    await db.refresh(review)
    return review


async def update(
    db: AsyncSession, review_id: uuid.UUID, current_user: User, payload: ReviewUpdateRequest
) -> Review:
    review = await _get_or_404(db, review_id)
    if review.client_id != current_user.id:
        raise ForbiddenError("Faqat sharh muallifi tahrirlay oladi")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(review, field, value)
    review.updated_at = datetime.now(UTC)
    await db.commit()

    if review.listing_id is not None:
        await listings_service.recompute_rating(db, review.listing_id)
    else:
        await tours_service.recompute_rating(db, review.tour_id)

    await db.refresh(review)
    return review


async def delete(db: AsyncSession, review_id: uuid.UUID, current_user: User) -> None:
    review = await _get_or_404(db, review_id)
    if review.client_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise ForbiddenError("Bu amal uchun ruxsatingiz yo'q")

    listing_id, tour_id = review.listing_id, review.tour_id
    await db.delete(review)
    await db.commit()

    if listing_id is not None:
        await listings_service.recompute_rating(db, listing_id)
    else:
        await tours_service.recompute_rating(db, tour_id)


async def list_for_target(
    db: AsyncSession,
    *,
    listing_id: uuid.UUID | None,
    tour_id: uuid.UUID | None,
    page: int,
    page_size: int,
) -> tuple[list[Review], int]:
    condition = (
        Review.listing_id == listing_id if listing_id is not None else Review.tour_id == tour_id
    )

    count_stmt = select(func.count()).select_from(Review).where(condition)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Review)
        .where(condition)
        .order_by(Review.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def list_mine(
    db: AsyncSession, client: User, page: int, page_size: int
) -> tuple[list[Review], int]:
    count_stmt = select(func.count()).select_from(Review).where(Review.client_id == client.id)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Review)
        .where(Review.client_id == client.id)
        .order_by(Review.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total
