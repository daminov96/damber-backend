import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.admin.models import AuditAction
from app.modules.users.schemas import UserOut


class BanUserRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class InviteAdminRequest(BaseModel):
    name: str
    surname: str
    phone: str
    password: str = Field(min_length=6)
    email: EmailStr | None = None


class RejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class ListingTypeStats(BaseModel):
    approved: int
    pending: int


class DashboardStatsOut(BaseModel):
    users_total: int
    users_by_role: dict[str, int]
    listings_total: int
    listings_pending: int
    listings_rejected: int
    listings_by_type: dict[str, ListingTypeStats]
    tours_total: int
    tours_pending: int
    tours_rejected: int
    total_revenue: float


class AuditLogEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    admin_id: uuid.UUID
    action: AuditAction
    target_type: str
    target_id: uuid.UUID
    detail: str | None
    created_at: datetime


class AuditLogListOut(BaseModel):
    items: list[AuditLogEntryOut]
    total: int
    page: int
    page_size: int


class AdminUserListOut(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int
