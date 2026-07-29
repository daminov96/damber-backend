import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.listings.models import Region


class RentCompanyCreateRequest(BaseModel):
    name: str
    tin: str = Field(pattern=r"^\d{9}$")
    license: str
    license_doc_name: str
    founded: int | None = None
    phone: str
    phone2: str | None = None
    email: str
    website: str | None = None
    office: str
    district: str | None = None
    region: Region
    lat: float | None = None
    lng: float | None = None
    location_link: str | None = None
    description: str
    work_hours: str | None = None
    pickup_zones: list[str] = Field(min_length=1)
    payment_methods: list[str] = Field(min_length=1)
    social_links: list[str] = Field(default_factory=list)
    bank_name: str | None = None
    bank_account: str | None = None
    bank_mfo: str | None = None
    logo: str | None = None


class RentCompanyUpdateRequest(BaseModel):
    name: str | None = None
    tin: str | None = Field(default=None, pattern=r"^\d{9}$")
    license: str | None = None
    license_doc_name: str | None = None
    founded: int | None = None
    phone: str | None = None
    phone2: str | None = None
    email: str | None = None
    website: str | None = None
    office: str | None = None
    district: str | None = None
    region: Region | None = None
    lat: float | None = None
    lng: float | None = None
    location_link: str | None = None
    description: str | None = None
    work_hours: str | None = None
    pickup_zones: list[str] | None = Field(default=None, min_length=1)
    payment_methods: list[str] | None = Field(default=None, min_length=1)
    social_links: list[str] | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    bank_mfo: str | None = None
    logo: str | None = None


class RentCompanyPhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    position: int


class RentCompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    tin: str
    license: str
    license_doc_name: str
    founded: int
    phone: str
    phone2: str | None
    email: str
    website: str | None
    office: str
    district: str | None
    region: Region
    lat: float | None
    lng: float | None
    location_link: str | None
    description: str
    work_hours: str | None
    pickup_zones: list[str]
    payment_methods: list[str]
    social_links: list[str]
    bank_name: str | None
    bank_account: str | None
    bank_mfo: str | None
    logo: str | None
    rating: float
    rating_count: int
    created_at: datetime
    photos: list[RentCompanyPhotoOut] = []


class RentCompanyListOut(BaseModel):
    items: list[RentCompanyOut]
    total: int
    page: int
    page_size: int
