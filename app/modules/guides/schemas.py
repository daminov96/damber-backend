import uuid
from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.guides.models import GuideEmployment, GuideType
from app.modules.listings.models import Region


class GuideCreateRequest(BaseModel):
    name: str
    avatar: str | None = None
    guide_type: GuideType = GuideType.Individual
    employment: GuideEmployment = GuideEmployment.Mustaqil
    license: str | None = None
    license_expiry: date | None = None
    license_doc_name: str | None = None
    tin: str | None = Field(default=None, pattern=r"^\d{9}$")
    languages: list[str] = Field(min_length=1)
    experience_years: int | None = None
    region: Region
    office: str | None = None
    service_areas: list[str] = Field(min_length=1)
    specialties: list[str] = Field(min_length=1)
    hourly_price: float | None = Field(default=None, gt=0)
    daily_price: float | None = Field(default=None, gt=0)
    price_includes: list[str] = Field(default_factory=lambda: ["Gidlik xizmati"])
    max_group_size: str | None = None
    cancellation_policy: str | None = None
    has_car: bool = False
    car_model: str | None = None
    car_seats: int | None = None
    phone: str
    email: str
    social_links: list[str] = Field(default_factory=list)
    video_url: str | None = None
    description: str = Field(min_length=20)

    @model_validator(mode="after")
    def check_business_rules(self) -> Self:
        if len(self.name.strip().split()) < 2:
            raise ValueError("F.I.SH. kamida 2 so'zdan iborat bo'lishi kerak")
        if not self.hourly_price and not self.daily_price:
            raise ValueError("Soatbay yoki kunlik narxdan kamida bittasi kiritilishi kerak")
        if self.has_car and not self.car_model:
            raise ValueError("Mashina bor deb belgilansa, model kiritilishi shart")
        return self


class GuideUpdateRequest(BaseModel):
    name: str | None = None
    avatar: str | None = None
    guide_type: GuideType | None = None
    employment: GuideEmployment | None = None
    license: str | None = None
    license_expiry: date | None = None
    license_doc_name: str | None = None
    tin: str | None = Field(default=None, pattern=r"^\d{9}$")
    languages: list[str] | None = Field(default=None, min_length=1)
    experience_years: int | None = None
    region: Region | None = None
    office: str | None = None
    service_areas: list[str] | None = Field(default=None, min_length=1)
    specialties: list[str] | None = Field(default=None, min_length=1)
    hourly_price: float | None = Field(default=None, gt=0)
    daily_price: float | None = Field(default=None, gt=0)
    price_includes: list[str] | None = None
    max_group_size: str | None = None
    cancellation_policy: str | None = None
    has_car: bool | None = None
    car_model: str | None = None
    car_seats: int | None = None
    phone: str | None = None
    email: str | None = None
    social_links: list[str] | None = None
    video_url: str | None = None
    description: str | None = Field(default=None, min_length=20)


class GuidePhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    position: int


class GuideOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    avatar: str | None
    guide_type: GuideType
    employment: GuideEmployment
    license: str | None
    license_expiry: date | None
    license_doc_name: str | None
    certified: bool
    tin: str | None
    languages: list[str]
    experience_years: int | None
    region: Region
    office: str | None
    service_areas: list[str]
    specialties: list[str]
    hourly_price: float | None
    daily_price: float | None
    price_includes: list[str]
    max_group_size: str | None
    cancellation_policy: str | None
    has_car: bool
    car_model: str | None
    car_seats: int | None
    phone: str
    email: str
    social_links: list[str]
    video_url: str | None
    description: str
    rating: float
    rating_count: int
    created_at: datetime
    photos: list[GuidePhotoOut] = []


class GuideListOut(BaseModel):
    items: list[GuideOut]
    total: int
    page: int
    page_size: int
