import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
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
from app.modules.listings.models import Region


class GuideType(enum.StrEnum):
    Individual = "Individual gid"
    Ekskursovod = "Ekskursovod / Hamroh"
    TogGidi = "Tog' gidi / Ekogid"
    GidHaydovchi = "Gid-haydovchi"


class GuideEmployment(enum.StrEnum):
    Mustaqil = "Mustaqil (yakka tartibdagi) gid"
    Turagentlik = "Turagentlik / turoperator xodimi"
    Muzey = "Muzey yoki qo'riqxona xodimi"


class GuideSortOption(enum.StrEnum):
    rating = "rating"
    name = "name"
    newest = "newest"


class Guide(Base):
    __tablename__ = "guides"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)

    name: Mapped[str] = mapped_column(String(200))
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    guide_type: Mapped[GuideType] = mapped_column(
        Enum(GuideType, name="guide_type"), default=GuideType.Individual
    )
    employment: Mapped[GuideEmployment] = mapped_column(
        Enum(GuideEmployment, name="guide_employment"), default=GuideEmployment.Mustaqil
    )

    license: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    license_doc_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    certified: Mapped[bool] = mapped_column(Boolean, default=False)
    tin: Mapped[str | None] = mapped_column(String(9), nullable=True)

    languages: Mapped[list[str]] = mapped_column(JSONB, default=list)
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    region: Mapped[Region] = mapped_column(Enum(Region, name="listing_region"), index=True)
    office: Mapped[str | None] = mapped_column(String(500), nullable=True)

    service_areas: Mapped[list[str]] = mapped_column(JSONB, default=list)
    specialties: Mapped[list[str]] = mapped_column(JSONB, default=list)

    hourly_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    daily_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    price_includes: Mapped[list[str]] = mapped_column(JSONB, default=lambda: ["Gidlik xizmati"])
    max_group_size: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cancellation_policy: Mapped[str | None] = mapped_column(String(500), nullable=True)

    has_car: Mapped[bool] = mapped_column(Boolean, default=False)
    car_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    car_seats: Mapped[int | None] = mapped_column(Integer, nullable=True)

    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(255))
    social_links: Mapped[list[str]] = mapped_column(JSONB, default=list)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    description: Mapped[str] = mapped_column(String(2000))

    rating: Mapped[float] = mapped_column(Float, default=0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    photos: Mapped[list["GuidePhoto"]] = relationship(
        back_populates="guide",
        cascade="all, delete-orphan",
        order_by="GuidePhoto.position",
    )


class GuidePhoto(Base):
    __tablename__ = "guide_photos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    guide_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("guides.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0)

    guide: Mapped["Guide"] = relationship(back_populates="photos")
