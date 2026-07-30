import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.listings.models import Region
from app.modules.tours.models import TourBookingStatus, TourDifficulty


class TourCreateRequest(BaseModel):
    operator_id: uuid.UUID | None = None
    guide_id: uuid.UUID | None = None
    name: str
    category: str | None = None
    duration: str
    nights: int | None = None
    region: Region
    departure_city: str | None = None
    meeting_point: str
    difficulty: TourDifficulty = TourDifficulty.Ortacha
    group_size: str | None = None

    price: float = Field(gt=0)
    old_price: float = 0
    extra_fee: float = 0
    extra_fee_note: str | None = None
    price_basis: str | None = None

    airline: str | None = None
    meal_plan: str | None = None
    seats_left: int | None = None

    description: str
    cancellation_policy: str | None = None
    video_url: str | None = None

    extra: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_exactly_one_owner_profile(self) -> Self:
        if (self.operator_id is None) == (self.guide_id is None):
            raise ValueError("operator_id yoki guide_id'dan aynan bittasi ko'rsatilishi kerak")
        return self


class TourUpdateRequest(BaseModel):
    name: str | None = None
    category: str | None = None
    duration: str | None = None
    nights: int | None = None
    region: Region | None = None
    departure_city: str | None = None
    meeting_point: str | None = None
    difficulty: TourDifficulty | None = None
    group_size: str | None = None

    price: float | None = Field(default=None, gt=0)
    old_price: float | None = None
    extra_fee: float | None = None
    extra_fee_note: str | None = None
    price_basis: str | None = None

    airline: str | None = None
    meal_plan: str | None = None
    seats_left: int | None = None

    description: str | None = None
    cancellation_policy: str | None = None
    video_url: str | None = None
    extra: dict | None = None


class TourPhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    position: int


class TourOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    operator_id: uuid.UUID | None
    guide_id: uuid.UUID | None
    owner_id: uuid.UUID
    name: str
    category: str | None
    duration: str
    nights: int | None
    region: Region
    departure_city: str | None
    meeting_point: str
    difficulty: TourDifficulty
    group_size: str | None
    price: float
    old_price: float
    extra_fee: float
    extra_fee_note: str | None
    price_basis: str | None
    airline: str | None
    meal_plan: str | None
    seats_left: int | None
    description: str
    cancellation_policy: str | None
    video_url: str | None
    extra: dict
    pending: bool
    rejected: bool
    reject_reason: str | None
    rating: float
    rating_count: int
    created_at: datetime
    photos: list[TourPhotoOut] = []


class TourListOut(BaseModel):
    items: list[TourOut]
    total: int
    page: int
    page_size: int


class TourBookingCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=9, max_length=20)
    people: int = Field(gt=0)


class TourBookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tour_id: uuid.UUID
    client_id: uuid.UUID
    name: str
    phone: str
    people: int
    total_estimate: float
    status: TourBookingStatus
    created_at: datetime


class TourBookingListOut(BaseModel):
    items: list[TourBookingOut]
    total: int
    page: int
    page_size: int
