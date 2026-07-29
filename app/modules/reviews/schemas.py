import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

SUBSCORE_CATEGORIES = frozenset({"cleanliness", "location", "service", "value", "comfort"})


def _check_sub_scores(sub_scores: dict[str, int]) -> None:
    invalid_keys = set(sub_scores) - SUBSCORE_CATEGORIES
    if invalid_keys:
        raise ValueError(f"Noto'g'ri sub_scores kaliti: {', '.join(sorted(invalid_keys))}")
    if not all(1 <= v <= 5 for v in sub_scores.values()):
        raise ValueError("sub_scores qiymatlari 1-5 oralig'ida bo'lishi kerak")


class ReviewCreateRequest(BaseModel):
    listing_id: uuid.UUID | None = None
    tour_id: uuid.UUID | None = None
    booking_id: uuid.UUID | None = None
    stars: int = Field(ge=1, le=5)
    text: str = Field(min_length=10, max_length=2000)
    sub_scores: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_target_and_booking(self) -> Self:
        if (self.listing_id is None) == (self.tour_id is None):
            raise ValueError("listing_id yoki tour_id'dan aynan bittasi ko'rsatilishi kerak")
        if self.listing_id is not None and self.booking_id is None:
            raise ValueError("Listing sharhi uchun booking_id majburiy")
        if self.tour_id is not None and self.booking_id is not None:
            raise ValueError("Tur sharhi uchun booking_id kerak emas")
        _check_sub_scores(self.sub_scores)
        return self


class ReviewUpdateRequest(BaseModel):
    stars: int | None = Field(default=None, ge=1, le=5)
    text: str | None = Field(default=None, min_length=10, max_length=2000)
    sub_scores: dict[str, int] | None = None

    @model_validator(mode="after")
    def check_sub_scores(self) -> Self:
        if self.sub_scores is not None:
            _check_sub_scores(self.sub_scores)
        return self


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    listing_id: uuid.UUID | None
    tour_id: uuid.UUID | None
    booking_id: uuid.UUID | None
    stars: int
    text: str
    sub_scores: dict[str, int]
    verified: bool
    created_at: datetime
    updated_at: datetime | None


class ReviewListOut(BaseModel):
    items: list[ReviewOut]
    total: int
    page: int
    page_size: int
