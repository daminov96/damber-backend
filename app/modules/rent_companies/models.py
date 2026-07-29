import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.modules.listings.models import Region


class RentCompanySortOption(enum.StrEnum):
    rating = "rating"
    name = "name"
    newest = "newest"


class RentCompany(Base):
    __tablename__ = "rent_companies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)

    name: Mapped[str] = mapped_column(String(200))
    tin: Mapped[str] = mapped_column(String(9))
    license: Mapped[str] = mapped_column(String(255))
    license_doc_name: Mapped[str] = mapped_column(String(255))
    founded: Mapped[int] = mapped_column(Integer)

    phone: Mapped[str] = mapped_column(String(20))
    phone2: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    office: Mapped[str] = mapped_column(String(500))
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[Region] = mapped_column(Enum(Region, name="listing_region"), index=True)

    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_link: Mapped[str | None] = mapped_column(String(500), nullable=True)

    description: Mapped[str] = mapped_column(String(5000))
    work_hours: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pickup_zones: Mapped[list[str]] = mapped_column(JSONB, default=list)
    payment_methods: Mapped[list[str]] = mapped_column(JSONB, default=list)
    social_links: Mapped[list[str]] = mapped_column(JSONB, default=list)

    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bank_account: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bank_mfo: Mapped[str | None] = mapped_column(String(20), nullable=True)

    logo: Mapped[str | None] = mapped_column(String(500), nullable=True)

    rating: Mapped[float] = mapped_column(Float, default=0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    photos: Mapped[list["RentCompanyPhoto"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        order_by="RentCompanyPhoto.position",
    )


class RentCompanyPhoto(Base):
    __tablename__ = "rent_company_photos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rent_companies.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0)

    company: Mapped["RentCompany"] = relationship(back_populates="photos")
