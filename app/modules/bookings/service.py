import uuid
from datetime import UTC, date, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.modules.bookings import pricing
from app.modules.bookings.models import Booking, BookingStatus, CancelledBy, EscrowStatus
from app.modules.bookings.schemas import BookingCreateRequest
from app.modules.listings.models import Listing
from app.modules.users.models import User, UserRole
from app.modules.wallet import service as wallet_service
from app.modules.wallet.models import WalletTxKind

ACTIVE_STATUSES = (BookingStatus.pending, BookingStatus.confirmed)
_STATUS_CONFLICT = "Bron holati bunga mos emas"


async def _get_listing(db: AsyncSession, listing_id: uuid.UUID) -> Listing:
    stmt = select(Listing).where(Listing.id == listing_id)
    listing = (await db.execute(stmt)).scalar_one_or_none()
    if not listing:
        raise NotFoundError("Listing topilmadi")
    return listing


async def _get_listing_locked(db: AsyncSession, listing_id: uuid.UUID) -> Listing:
    stmt = select(Listing).where(Listing.id == listing_id).with_for_update()
    listing = (await db.execute(stmt)).scalar_one_or_none()
    if not listing:
        raise NotFoundError("Listing topilmadi")
    return listing


async def _get_or_404(db: AsyncSession, booking_id: uuid.UUID) -> Booking:
    stmt = select(Booking).where(Booking.id == booking_id)
    booking = (await db.execute(stmt)).scalar_one_or_none()
    if not booking:
        raise NotFoundError("Bron topilmadi")
    return booking


async def _load_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise NotFoundError("Foydalanuvchi topilmadi")
    return user


def _check_participant_or_admin(booking: Booking, user: User) -> None:
    if user.id not in (booking.client_id, booking.owner_id) and user.role != UserRole.ADMIN:
        raise ForbiddenError("Bu amal uchun ruxsatingiz yo'q")


def _check_client(booking: Booking, user: User) -> None:
    if booking.client_id != user.id:
        raise ForbiddenError("Bu amal uchun ruxsatingiz yo'q")


def _check_host(booking: Booking, user: User) -> None:
    if booking.owner_id != user.id and user.role != UserRole.ADMIN:
        raise ForbiddenError("Bu amal uchun ruxsatingiz yo'q")


async def quote(
    db: AsyncSession,
    listing_id: uuid.UUID,
    check_in: date,
    check_out: date,
    guests: int,
    promo_code: str | None,
) -> pricing.BookingQuote:
    listing = await _get_listing(db, listing_id)
    if check_out <= check_in:
        raise HTTPException(400, detail="check_out check_in dan keyin bo'lishi kerak")
    return pricing.quote(listing, check_in, check_out, guests, promo_code, date.today())


async def _assert_no_overlap(
    db: AsyncSession, listing_id: uuid.UUID, check_in: date, check_out: date
) -> None:
    stmt = (
        select(Booking.id)
        .where(
            Booking.listing_id == listing_id,
            Booking.status.in_(ACTIVE_STATUSES),
            Booking.check_in < check_out,
            Booking.check_out > check_in,
        )
        .limit(1)
    )
    if (await db.execute(stmt)).first():
        raise ConflictError("Bu sanalar band")


async def create(db: AsyncSession, client: User, payload: BookingCreateRequest) -> Booking:
    # Listing qatori qulflanadi — shu listing uchun parallel create() chaqiruvlari
    # ushbu tranzaksiya tugaguncha kutadi (kesishuv tekshiruvi shu qulf ostida bo'ladi).
    listing = await _get_listing_locked(db, payload.listing_id)

    q = pricing.quote(
        listing,
        payload.check_in,
        payload.check_out,
        payload.guests,
        payload.promo_code,
        date.today(),
    )
    if q.over_capacity:
        raise HTTPException(400, detail="Mehmonlar soni sig'imdan oshib ketdi")
    nights = q.weekdays + q.weekends
    if nights < q.min_stay:
        raise HTTPException(400, detail=f"Minimal qolish muddati {q.min_stay} tun")
    if q.blocked_in_range:
        raise HTTPException(400, detail="Tanlangan sanalarda band kunlar bor")

    await _assert_no_overlap(db, listing.id, payload.check_in, payload.check_out)

    extra = listing.extra or {}
    cancellation_policy = (extra.get("rules") or {}).get("cancellation")

    booking = Booking(
        listing_id=listing.id,
        client_id=client.id,
        owner_id=listing.owner_id,
        check_in=payload.check_in,
        check_out=payload.check_out,
        guests=payload.guests,
        status=BookingStatus.pending,
        total_amount=q.total,
        advance_amount=q.advance,
        prepay_percent=q.prepay_percent,
        escrow=None,
        cancellation_policy=cancellation_policy,
        promo_code=payload.promo_code,
        guest_name=payload.guest_name,
        guest_phone=payload.guest_phone,
        guest_email=payload.guest_email,
        guest_type=payload.guest_type,
        message=payload.message,
    )

    if q.advance > 0:
        await wallet_service.pay(
            db,
            client,
            q.advance,
            "Bron avansi — eskrovda",
            kind=WalletTxKind.booking,
            ref=str(booking.id),
        )
        booking.escrow = EscrowStatus.held

    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking


async def get_by_id(db: AsyncSession, booking_id: uuid.UUID, user: User) -> Booking:
    booking = await _get_or_404(db, booking_id)
    _check_participant_or_admin(booking, user)
    return booking


async def list_mine(
    db: AsyncSession, client: User, page: int, page_size: int
) -> tuple[list[Booking], int]:
    count_stmt = select(func.count()).select_from(Booking).where(Booking.client_id == client.id)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Booking)
        .where(Booking.client_id == client.id)
        .order_by(Booking.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def list_for_host(
    db: AsyncSession, owner: User, status: BookingStatus | None, page: int, page_size: int
) -> tuple[list[Booking], int]:
    conditions = [Booking.owner_id == owner.id]
    if status is not None:
        conditions.append(Booking.status == status)

    count_stmt = select(func.count()).select_from(Booking).where(*conditions)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Booking)
        .where(*conditions)
        .order_by(Booking.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def confirm(db: AsyncSession, booking_id: uuid.UUID, host: User) -> Booking:
    booking = await _get_or_404(db, booking_id)
    _check_host(booking, host)
    if booking.status != BookingStatus.pending:
        raise ConflictError(_STATUS_CONFLICT)
    booking.status = BookingStatus.confirmed
    booking.confirmed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(booking)
    return booking


async def reject(
    db: AsyncSession, booking_id: uuid.UUID, host: User, reason: str | None
) -> Booking:
    booking = await _get_or_404(db, booking_id)
    _check_host(booking, host)
    if booking.status != BookingStatus.pending:
        raise ConflictError(_STATUS_CONFLICT)

    if booking.escrow == EscrowStatus.held and float(booking.advance_amount) > 0:
        client = await _load_user(db, booking.client_id)
        r = pricing.host_reject_refund(float(booking.advance_amount))
        if r.amount > 0:
            await wallet_service.credit(
                db,
                client,
                r.amount,
                "Bron rad etildi — avans qaytarildi",
                kind=WalletTxKind.refund,
                ref=str(booking.id),
            )
        booking.refund_amount = r.amount
        booking.escrow = EscrowStatus.refunded

    booking.status = BookingStatus.rejected
    booking.reject_reason = reason
    booking.cancelled_by = CancelledBy.host
    await db.commit()
    await db.refresh(booking)
    return booking


async def complete(db: AsyncSession, booking_id: uuid.UUID, host: User) -> Booking:
    booking = await _get_or_404(db, booking_id)
    _check_host(booking, host)
    if booking.status != BookingStatus.confirmed:
        raise ConflictError(_STATUS_CONFLICT)

    if booking.escrow == EscrowStatus.held and float(booking.advance_amount) > 0:
        owner = await _load_user(db, booking.owner_id)
        await wallet_service.credit(
            db,
            owner,
            float(booking.advance_amount),
            "Bron yakunlandi — avans to'lovi",
            kind=WalletTxKind.booking,
            ref=str(booking.id),
        )
        booking.escrow = EscrowStatus.released

    booking.status = BookingStatus.completed
    await db.commit()
    await db.refresh(booking)
    return booking


async def cancel(
    db: AsyncSession, booking_id: uuid.UUID, client: User, now: datetime | None = None
) -> Booking:
    """`now` — faqat testlar uchun ixtiyoriy (bekor qilish siyosati soatiga aniq
    ta'sir qilish uchun), public chaqiruvchilar bermaydi."""
    booking = await _get_or_404(db, booking_id)
    _check_client(booking, client)
    if booking.status not in (BookingStatus.pending, BookingStatus.confirmed):
        raise ConflictError(_STATUS_CONFLICT)

    if booking.escrow == EscrowStatus.held and float(booking.advance_amount) > 0:
        advance = float(booking.advance_amount)
        r = pricing.guest_refund(booking.cancellation_policy, booking.check_in, advance, now)
        if r.amount > 0:
            await wallet_service.credit(
                db,
                client,
                r.amount,
                "Bron bekor qilindi — avans qaytarildi",
                kind=WalletTxKind.refund,
                ref=str(booking.id),
            )
        if r.burnt > 0:
            owner = await _load_user(db, booking.owner_id)
            await wallet_service.credit(
                db,
                owner,
                r.burnt,
                "Bekor qilingan bron — kompensatsiya",
                kind=WalletTxKind.booking,
                ref=str(booking.id),
            )
        booking.refund_amount = r.amount
        booking.escrow = EscrowStatus.refunded

    booking.status = BookingStatus.cancelled
    booking.cancelled_by = CancelledBy.guest
    await db.commit()
    await db.refresh(booking)
    return booking


async def restore(db: AsyncSession, booking_id: uuid.UUID, host: User) -> Booking:
    booking = await _get_or_404(db, booking_id)
    _check_host(booking, host)
    if booking.status != BookingStatus.rejected:
        raise ConflictError(_STATUS_CONFLICT)

    if booking.escrow == EscrowStatus.refunded and (booking.refund_amount or 0) > 0:
        client = await _load_user(db, booking.client_id)
        await wallet_service.pay(
            db,
            client,
            float(booking.refund_amount),
            "Bron qayta tiklandi — avans qayta ushlandi",
            kind=WalletTxKind.booking,
            ref=str(booking.id),
        )
        booking.escrow = EscrowStatus.held

    booking.status = BookingStatus.pending
    booking.refund_amount = None
    booking.cancelled_by = None
    booking.reject_reason = None
    await db.commit()
    await db.refresh(booking)
    return booking
