import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.plans.catalog import PlanId
from app.modules.users.models import BillingCycle


class PlanPurchase(Base):
    __tablename__ = "plan_purchases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)

    plan_id: Mapped[PlanId] = mapped_column(Enum(PlanId, name="plan_id_enum"))
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        Enum(BillingCycle, name="plan_billing_cycle")
    )
    price_paid: Mapped[float] = mapped_column(Numeric(14, 2))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
