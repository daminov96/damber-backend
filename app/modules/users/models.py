import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class UserRole(enum.StrEnum):
    B2C = "B2C"
    B2B = "B2B"
    ADMIN = "ADMIN"


class AdminRole(enum.StrEnum):
    """ADMIN foydalanuvchisining panel ichidagi huquq darajasi.

    Faqat `role == UserRole.ADMIN` bo'lganda mazmunli — boshqa rollarda
    doim `None`. Qaysi daraja qaysi panel bo'limiga kira olishi
    `app/modules/admin/permissions.py::ROLE_MATRIX`da belgilanadi."""

    super = "super"
    moderator = "moderator"
    finance = "finance"
    content = "content"


class BillingCycle(enum.StrEnum):
    monthly = "monthly"
    yearly = "yearly"


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "(role = 'ADMIN') OR (admin_role IS NULL)",
            name="ck_users_admin_role_only_for_admin",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    surname: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.B2C)

    wallet_balance: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    is_premium: Mapped[bool] = mapped_column(default=False)
    current_plan_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    plan_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    plan_period: Mapped[BillingCycle | None] = mapped_column(
        Enum(BillingCycle, name="plan_billing_cycle"), nullable=True
    )
    plan_rate: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    biz_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    banned_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    admin_role: Mapped[AdminRole | None] = mapped_column(
        Enum(AdminRole, name="admin_role"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
