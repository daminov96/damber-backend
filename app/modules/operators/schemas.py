import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.listings.models import Region
from app.modules.operators.models import OperatorSpecTag


class OperatorCreateRequest(BaseModel):
    name: str
    tin: str = Field(pattern=r"^\d{9}$")
    license: str
    license_doc_name: str | None = None
    license_expiry: date
    founded: int | None = None
    spec_tag: OperatorSpecTag = OperatorSpecTag.Tarixiy
    phone: str
    email: str
    website: str | None = None
    office: str
    region: Region
    lat: float | None = None
    lng: float | None = None
    location_link: str | None = None
    description: str
    social_links: list[str] = Field(default_factory=list)
    video_url: str | None = None


class OperatorUpdateRequest(BaseModel):
    name: str | None = None
    tin: str | None = Field(default=None, pattern=r"^\d{9}$")
    license: str | None = None
    license_doc_name: str | None = None
    license_expiry: date | None = None
    founded: int | None = None
    spec_tag: OperatorSpecTag | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    office: str | None = None
    region: Region | None = None
    lat: float | None = None
    lng: float | None = None
    location_link: str | None = None
    description: str | None = None
    social_links: list[str] | None = None
    video_url: str | None = None


class TourOperatorPhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    position: int


class TourOperatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    tin: str
    license: str
    license_doc_name: str | None
    license_issued: str | None
    license_expiry: date | None
    founded: int
    spec_tag: OperatorSpecTag
    phone: str
    email: str
    website: str | None
    office: str
    region: Region
    lat: float | None
    lng: float | None
    location_link: str | None
    description: str
    social_links: list[str]
    video_url: str | None
    rating: float
    rating_count: int
    created_at: datetime
    photos: list[TourOperatorPhotoOut] = []


class TourOperatorListOut(BaseModel):
    items: list[TourOperatorOut]
    total: int
    page: int
    page_size: int
