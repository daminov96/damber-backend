import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.plans.catalog import PlanId
from app.modules.plans.models import BillingCycle


class PlanOut(BaseModel):
    id: PlanId
    name: str
    price: float
    yearly_price: float
    photo_limit: int
    video_limit: int
    video_size_mb: int
    badge: str | None
    emblem: str | None
    features: list[str]


class PlanCatalogOut(BaseModel):
    items: list[PlanOut]


class MyPlanOut(BaseModel):
    current_plan_id: PlanId
    plan: PlanOut


class PlanSwitchRequest(BaseModel):
    plan_id: PlanId
    billing_cycle: BillingCycle = BillingCycle.monthly


class PlanPurchaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_id: PlanId
    billing_cycle: BillingCycle
    price_paid: float
    created_at: datetime


class PlanPurchaseListOut(BaseModel):
    items: list[PlanPurchaseOut]
    total: int
    page: int
    page_size: int
