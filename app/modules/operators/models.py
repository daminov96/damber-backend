import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.modules.listings.models import Region


class OperatorSpecTag(enum.StrEnum):
    Tarixiy = "Tarixiy"
    Ekoturizm = "Ekoturizm"
    Xalqaro = "Xalqaro"
    HajUmra = "HajUmra"


SPEC_LABELS: dict[str, str] = {
    "Tarixiy": "Tarixiy va madaniy turlar",
    "Ekoturizm": "Ekoturizm va tog' trekkingi",
    "Xalqaro": "Xalqaro dam olish turlari",
    "HajUmra": "Haj va Umra safarlari",
}


class OperatorSortOption(enum.StrEnum):
    rating = "rating"
    name = "name"
    newest = "newest"


class TourOperator(Base):
    __tablename__ = "tour_operators"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)

    name: Mapped[str] = mapped_column(String(200))
    tin: Mapped[str] = mapped_column(String(9))
    license: Mapped[str] = mapped_column(String(255))
    license_doc_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_issued: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)

    founded: Mapped[int] = mapped_column(Integer)
    spec_tag: Mapped[OperatorSpecTag] = mapped_column(
        Enum(OperatorSpecTag, name="operator_spec_tag"), default=OperatorSpecTag.Tarixiy
    )

    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    office: Mapped[str] = mapped_column(String(500))
    region: Mapped[Region] = mapped_column(Enum(Region, name="listing_region"), index=True)

    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_link: Mapped[str | None] = mapped_column(String(500), nullable=True)

    description: Mapped[str] = mapped_column(String(5000))
    social_links: Mapped[list[str]] = mapped_column(JSONB, default=list)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    rating: Mapped[float] = mapped_column(Float, default=0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    photos: Mapped[list["TourOperatorPhoto"]] = relationship(
        back_populates="operator",
        cascade="all, delete-orphan",
        order_by="TourOperatorPhoto.position",
    )


class TourOperatorPhoto(Base):
    __tablename__ = "tour_operator_photos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    operator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tour_operators.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0)

    operator: Mapped["TourOperator"] = relationship(back_populates="photos")
