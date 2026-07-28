import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class BookingStatus(enum.StrEnum):
    pending = "pending"
    confirmed = "confirmed"
    completed = "completed"
    rejected = "rejected"
    cancelled = "cancelled"


class EscrowStatus(enum.StrEnum):
    held = "held"
    released = "released"
    refunded = "refunded"


class CancelledBy(enum.StrEnum):
    guest = "guest"
    host = "host"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)

    check_in: Mapped[date] = mapped_column(Date)
    check_out: Mapped[date] = mapped_column(Date)
    guests: Mapped[int] = mapped_column(Integer)

    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status"), default=BookingStatus.pending, index=True
    )

    total_amount: Mapped[float] = mapped_column(Numeric(14, 2))
    advance_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    prepay_percent: Mapped[int] = mapped_column(Integer)
    escrow: Mapped[EscrowStatus | None] = mapped_column(
        Enum(EscrowStatus, name="booking_escrow_status"), nullable=True
    )

    cancellation_policy: Mapped[str | None] = mapped_column(String(500), nullable=True)
    promo_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    guest_name: Mapped[str] = mapped_column(String(150))
    guest_phone: Mapped[str] = mapped_column(String(20))
    guest_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guest_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    reject_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    refund_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    cancelled_by: Mapped[CancelledBy | None] = mapped_column(
        Enum(CancelledBy, name="booking_cancelled_by"), nullable=True
    )

    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
