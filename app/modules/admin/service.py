import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.modules.admin.models import AdminAuditLog, AuditAction
from app.modules.admin.schemas import DashboardStatsOut, InviteAdminRequest
from app.modules.bookings.models import Booking, BookingStatus
from app.modules.listings.models import Listing
from app.modules.tours.models import Tour
from app.modules.users.models import User, UserRole


def _normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone)


async def log_action(
    db: AsyncSession,
    admin: User,
    action: AuditAction,
    target_type: str,
    target_id: uuid.UUID,
    detail: str | None = None,
) -> AdminAuditLog:
    entry = AdminAuditLog(
        admin_id=admin.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def _get_user_or_404(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise NotFoundError("Foydalanuvchi topilmadi")
    return user


async def ban_user(db: AsyncSession, user_id: uuid.UUID, admin: User, reason: str) -> User:
    user = await _get_user_or_404(db, user_id)
    if user.role == UserRole.ADMIN:
        raise ForbiddenError("Adminni bloklab bo'lmaydi")
    user.is_banned = True
    user.banned_reason = reason
    await db.commit()
    await db.refresh(user)
    await log_action(db, admin, AuditAction.user_ban, "user", user_id, reason)
    return user


async def unban_user(db: AsyncSession, user_id: uuid.UUID, admin: User) -> User:
    user = await _get_user_or_404(db, user_id)
    user.is_banned = False
    user.banned_reason = None
    await db.commit()
    await db.refresh(user)
    await log_action(db, admin, AuditAction.user_unban, "user", user_id)
    return user


async def invite_admin(db: AsyncSession, admin: User, payload: InviteAdminRequest) -> User:
    phone = _normalize_phone(payload.phone)
    existing = await db.execute(select(User).where(User.phone == phone))
    if existing.scalar_one_or_none():
        raise ConflictError("Bu telefon raqam allaqachon ro'yxatdan o'tgan")

    new_admin = User(
        name=payload.name,
        surname=payload.surname,
        phone=phone,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.ADMIN,
    )
    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)
    await log_action(db, admin, AuditAction.admin_invite, "user", new_admin.id, phone)
    return new_admin


async def list_users(
    db: AsyncSession,
    role: UserRole | None,
    is_banned: bool | None,
    query: str | None,
    page: int,
    page_size: int,
) -> tuple[list[User], int]:
    conditions = []
    if role is not None:
        conditions.append(User.role == role)
    if is_banned is not None:
        conditions.append(User.is_banned == is_banned)
    if query:
        like = f"%{query}%"
        conditions.append(
            (User.name.ilike(like)) | (User.surname.ilike(like)) | (User.phone.ilike(like))
        )

    count_stmt = select(func.count()).select_from(User).where(*conditions)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(User)
        .where(*conditions)
        .order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def get_dashboard_stats(db: AsyncSession) -> DashboardStatsOut:
    users_total = (await db.execute(select(func.count()).select_from(User))).scalar_one()

    role_rows = (await db.execute(select(User.role, func.count()).group_by(User.role))).all()
    users_by_role = {role.value: count for role, count in role_rows}

    listings_total = (await db.execute(select(func.count()).select_from(Listing))).scalar_one()
    listings_pending = (
        await db.execute(
            select(func.count())
            .select_from(Listing)
            .where(Listing.verified.is_(False), Listing.rejected.is_(False))
        )
    ).scalar_one()
    listings_rejected = (
        await db.execute(
            select(func.count()).select_from(Listing).where(Listing.rejected.is_(True))
        )
    ).scalar_one()

    tours_total = (await db.execute(select(func.count()).select_from(Tour))).scalar_one()
    tours_pending = (
        await db.execute(
            select(func.count())
            .select_from(Tour)
            .where(Tour.pending.is_(True), Tour.rejected.is_(False))
        )
    ).scalar_one()
    tours_rejected = (
        await db.execute(select(func.count()).select_from(Tour).where(Tour.rejected.is_(True)))
    ).scalar_one()

    revenue = (
        await db.execute(
            select(func.sum(Booking.total_amount)).where(Booking.status == BookingStatus.completed)
        )
    ).scalar_one()

    return DashboardStatsOut(
        users_total=users_total,
        users_by_role=users_by_role,
        listings_total=listings_total,
        listings_pending=listings_pending,
        listings_rejected=listings_rejected,
        tours_total=tours_total,
        tours_pending=tours_pending,
        tours_rejected=tours_rejected,
        total_revenue=float(revenue) if revenue is not None else 0.0,
    )


async def list_audit_log(
    db: AsyncSession, action: AuditAction | None, page: int, page_size: int
) -> tuple[list[AdminAuditLog], int]:
    conditions = []
    if action is not None:
        conditions.append(AdminAuditLog.action == action)

    count_stmt = select(func.count()).select_from(AdminAuditLog).where(*conditions)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(AdminAuditLog)
        .where(*conditions)
        .order_by(AdminAuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total
