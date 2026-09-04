import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FavoriteCreateRequest(BaseModel):
    listing_id: uuid.UUID


class FavoriteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    created_at: datetime


class FavoriteListOut(BaseModel):
    items: list[FavoriteOut]
    total: int
    page: int
    page_size: int
