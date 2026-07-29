import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Review(Base):
    __tablename__ = "reviews"

    __table_args__ = (
        CheckConstraint(
            "(listing_id IS NOT NULL AND tour_id IS NULL) OR "
            "(listing_id IS NULL AND tour_id IS NOT NULL)",
            name="ck_reviews_exactly_one_target",
        ),
        UniqueConstraint("client_id", "tour_id", name="uq_reviews_client_tour"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), nullable=True, index=True
    )
    tour_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tours.id", ondelete="CASCADE"), nullable=True, index=True
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bookings.id"), nullable=True, unique=True, index=True
    )

    stars: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(String(2000))
    sub_scores: Mapped[dict] = mapped_column(JSONB, default=dict)
    verified: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
