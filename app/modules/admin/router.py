import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_role
from app.modules.admin import service
from app.modules.admin.models import AuditAction
from app.modules.admin.schemas import (
    AdminUserListOut,
    AuditLogListOut,
    BanUserRequest,
    DashboardStatsOut,
    InviteAdminRequest,
)
from app.modules.listings import service as listings_service
from app.modules.listings.schemas import ListingListOut
from app.modules.tours import service as tours_service
from app.modules.tours.schemas import TourListOut
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import UserOut

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]


@router.get("/dashboard", response_model=DashboardStatsOut)
async def dashboard(current_user: AdminUser, db: AsyncSession = Depends(get_db)):
    return await service.get_dashboard_stats(db)


@router.get("/users", response_model=AdminUserListOut)
async def list_users(
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
    role: UserRole | None = Query(None),
    is_banned: bool | None = Query(None),
    query: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.list_users(db, role, is_banned, query, page, page_size)
    return AdminUserListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/users/invite-admin", response_model=UserOut, status_code=201)
async def invite_admin(
    payload: InviteAdminRequest, current_user: AdminUser, db: AsyncSession = Depends(get_db)
):
    return await service.invite_admin(db, current_user, payload)


@router.post("/users/{user_id}/ban", response_model=UserOut)
async def ban_user(
    user_id: uuid.UUID,
    payload: BanUserRequest,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.ban_user(db, user_id, current_user, payload.reason)


@router.post("/users/{user_id}/unban", response_model=UserOut)
async def unban_user(
    user_id: uuid.UUID, current_user: AdminUser, db: AsyncSession = Depends(get_db)
):
    return await service.unban_user(db, user_id, current_user)


@router.get("/moderation/listings", response_model=ListingListOut)
async def moderation_listings(
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await listings_service.list_pending(db, page, page_size)
    return ListingListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/moderation/tours", response_model=TourListOut)
async def moderation_tours(
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await tours_service.list_pending(db, page, page_size)
    return TourListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/audit-log", response_model=AuditLogListOut)
async def audit_log(
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
    action: AuditAction | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.list_audit_log(db, action, page, page_size)
    return AuditLogListOut(items=items, total=total, page=page, page_size=page_size)
