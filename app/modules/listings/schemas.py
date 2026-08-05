import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.listings.models import AMENITY_VALUES, ListingType, Region


def _validate_amenities(value: list[str]) -> list[str]:
    invalid = [a for a in value if a not in AMENITY_VALUES]
    if invalid:
        raise ValueError(f"Noto'g'ri amenity qiymat(lar)i: {', '.join(invalid)}")
    return value


class ListingCreateRequest(BaseModel):
    name: str
    type: ListingType
    region: Region
    weekday_price: float = Field(gt=0)
    weekend_price: float = Field(gt=0)
    old_price: float | None = Field(default=None, gt=0)
    capacity: int = Field(gt=0)
    amenities: list[str] = Field(default_factory=list)
    description: str
    license: str | None = None
    license_expiry: date | None = None
    company_id: uuid.UUID | None = None
    extra: dict = Field(default_factory=dict)

    @field_validator("amenities")
    @classmethod
    def check_amenities(cls, v: list[str]) -> list[str]:
        return _validate_amenities(v)


class ListingUpdateRequest(BaseModel):
    name: str | None = None
    type: ListingType | None = None
    region: Region | None = None
    weekday_price: float | None = Field(default=None, gt=0)
    weekend_price: float | None = Field(default=None, gt=0)
    old_price: float | None = Field(default=None, gt=0)
    capacity: int | None = Field(default=None, gt=0)
    amenities: list[str] | None = None
    description: str | None = None
    license: str | None = None
    license_expiry: date | None = None
    license_doc_url: str | None = None
    video_url: str | None = None
    discount: int | None = None
    company_id: uuid.UUID | None = None
    extra: dict | None = None

    @field_validator("amenities")
    @classmethod
    def check_amenities(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        return _validate_amenities(v)


class ListingPhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    position: int


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    company_id: uuid.UUID | None
    name: str
    type: ListingType
    region: Region
    weekday_price: float
    weekend_price: float
    old_price: float | None
    rating: float
    rating_count: int
    verified: bool
    paused: bool
    rejected: bool
    reject_reason: str | None
    capacity: int
    amenities: list[str]
    description: str
    license: str | None
    license_expiry: date | None
    license_doc_url: str | None
    video_url: str | None
    views: int
    saves: int
    is_hot: bool
    discount: int
    extra: dict
    created_at: datetime
    photos: list[ListingPhotoOut] = []


class ListingListOut(BaseModel):
    items: list[ListingOut]
    total: int
    page: int
    page_size: int


class UploadFileOut(BaseModel):
    url: str
