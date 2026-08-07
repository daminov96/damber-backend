import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.modules.guides.models import Guide
from app.modules.listings.models import Region
from app.modules.operators.models import SPEC_LABELS, TourOperator


class TourDifficulty(enum.StrEnum):
    Oson = "Oson"
    Ortacha = "O'rtacha"
    Qiyin = "Qiyin"
    Ekstremal = "Ekstremal"


class TourSortOption(enum.StrEnum):
    rating = "rating"
    newest = "newest"
    price_asc = "price_asc"
    price_desc = "price_desc"


class TourBookingStatus(enum.StrEnum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"


class Tour(Base):
    __tablename__ = "tours"

    __table_args__ = (
        CheckConstraint(
            "(operator_id IS NOT NULL AND guide_id IS NULL) OR "
            "(operator_id IS NULL AND guide_id IS NOT NULL)",
            name="ck_tours_exactly_one_owner_profile",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    operator_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tour_operators.id"), nullable=True, index=True
    )
    guide_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("guides.id"), nullable=True, index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)

    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration: Mapped[str] = mapped_column(String(100))
    nights: Mapped[int | None] = mapped_column(Integer, nullable=True)
    region: Mapped[Region] = mapped_column(Enum(Region, name="listing_region"), index=True)
    departure_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    meeting_point: Mapped[str] = mapped_column(String(500))
    difficulty: Mapped[TourDifficulty] = mapped_column(
        Enum(TourDifficulty, name="tour_difficulty"), default=TourDifficulty.Ortacha
    )
    group_size: Mapped[str | None] = mapped_column(String(100), nullable=True)

    price: Mapped[float] = mapped_column(Numeric(14, 2))
    old_price: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    extra_fee: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    extra_fee_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price_basis: Mapped[str | None] = mapped_column(String(200), nullable=True)

    airline: Mapped[str | None] = mapped_column(String(100), nullable=True)
    meal_plan: Mapped[str | None] = mapped_column(String(100), nullable=True)
    seats_left: Mapped[int | None] = mapped_column(Integer, nullable=True)

    description: Mapped[str] = mapped_column(String(5000))
    cancellation_policy: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    extra: Mapped[dict] = mapped_column(JSONB, default=dict)

    pending: Mapped[bool] = mapped_column(Boolean, default=True)
    rejected: Mapped[bool] = mapped_column(Boolean, default=False)
    reject_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rating: Mapped[float] = mapped_column(Float, default=0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    photos: Mapped[list["TourPhoto"]] = relationship(
        back_populates="tour",
        cascade="all, delete-orphan",
        order_by="TourPhoto.position",
    )
    operator: Mapped["TourOperator | None"] = relationship(lazy="selectin", viewonly=True)
    guide: Mapped["Guide | None"] = relationship(lazy="selectin", viewonly=True)

    @property
    def operator_name(self) -> str:
        return self.operator.name if self.operator else self.guide.name

    @property
    def operator_license(self) -> str | None:
        return self.operator.license if self.operator else self.guide.license

    @property
    def operator_phone(self) -> str:
        return self.operator.phone if self.operator else self.guide.phone

    @property
    def operator_email(self) -> str:
        return self.operator.email if self.operator else self.guide.email

    @property
    def operator_website(self) -> str | None:
        return self.operator.website if self.operator else None

    @property
    def operator_social_links(self) -> list[str]:
        return self.operator.social_links if self.operator else self.guide.social_links

    @property
    def operator_tagline(self) -> str | None:
        if not self.operator:
            return None
        return SPEC_LABELS.get(self.operator.spec_tag.value)


class TourPhoto(Base):
    __tablename__ = "tour_photos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tour_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tours.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0)

    tour: Mapped["Tour"] = relationship(back_populates="photos")


class TourBooking(Base):
    __tablename__ = "tour_bookings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tour_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tours.id"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)

    name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(20))
    people: Mapped[int] = mapped_column(Integer)
    total_estimate: Mapped[float] = mapped_column(Numeric(14, 2))

    status: Mapped[TourBookingStatus] = mapped_column(
        Enum(TourBookingStatus, name="tour_booking_status"), default=TourBookingStatus.pending
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
