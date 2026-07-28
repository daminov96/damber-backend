import uuid
from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.bookings.models import BookingStatus, CancelledBy, EscrowStatus


class BookingQuoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    weekdays: int
    weekends: int
    weekday_sum: float
    weekend_sum: float
    season_nights: int
    season_extra: float
    promo_label: str | None
    promo_amount: float
    subtotal: float
    code_discount: float
    total: float
    prepay_percent: int
    advance: float
    remainder: float
    min_stay: int
    blocked_in_range: list[str]
    over_capacity: bool


class BookingCreateRequest(BaseModel):
    listing_id: uuid.UUID
    check_in: date
    check_out: date
    guests: int = Field(gt=0)
    promo_code: str | None = None
    guest_name: str = Field(min_length=2, max_length=150)
    guest_phone: str = Field(min_length=5, max_length=20)
    guest_email: str | None = None
    guest_type: str | None = None
    message: str | None = None

    @model_validator(mode="after")
    def check_dates(self) -> Self:
        if self.check_out <= self.check_in:
            raise ValueError("check_out check_in dan keyin bo'lishi kerak")
        return self


class BookingRejectRequest(BaseModel):
    reason: str | None = None


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    client_id: uuid.UUID
    owner_id: uuid.UUID
    check_in: date
    check_out: date
    guests: int
    status: BookingStatus
    total_amount: float
    advance_amount: float
    prepay_percent: int
    escrow: EscrowStatus | None
    cancellation_policy: str | None
    promo_code: str | None
    guest_name: str
    guest_phone: str
    guest_email: str | None
    guest_type: str | None
    message: str | None
    reject_reason: str | None
    refund_amount: float | None
    cancelled_by: CancelledBy | None
    confirmed_at: datetime | None
    created_at: datetime


class BookingListOut(BaseModel):
    items: list[BookingOut]
    total: int
    page: int
    page_size: int
