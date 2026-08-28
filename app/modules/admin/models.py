import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AuditAction(enum.StrEnum):
    listing_approve = "listing_approve"
    listing_reject = "listing_reject"
    listing_pause = "listing_pause"
    tour_approve = "tour_approve"
    tour_reject = "tour_reject"
    review_delete = "review_delete"
    user_ban = "user_ban"
    user_unban = "user_unban"
    admin_invite = "admin_invite"
    admin_role_change = "admin_role_change"
    admin_delete = "admin_delete"


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # `SET NULL` — admin hisobi o'chirilgan (`DELETE /admin/users/{id}`)
    # bo'lsa ham audit tarixi saqlanadi, faqat "kim qilgani" ma'lumoti
    # yo'qoladi (nima qilingani `action`/`target_*`da qoladi).
    admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction, name="admin_audit_action"))
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
