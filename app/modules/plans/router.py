from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_role
from app.modules.plans import service
from app.modules.plans.schemas import (
    MyPlanOut,
    PlanCatalogOut,
    PlanPurchaseListOut,
    PlanSwitchRequest,
)
from app.modules.users.models import User, UserRole

router = APIRouter(prefix="/api/v1", tags=["plans"])


@router.get("/plans", response_model=PlanCatalogOut)
async def list_plans():
    return PlanCatalogOut(items=service.get_catalog())


@router.get("/plans/mine", response_model=MyPlanOut)
async def my_plan(current_user: Annotated[User, Depends(require_role(UserRole.B2B))]):
    return service.get_my_plan(current_user)


@router.post("/plans/switch", response_model=MyPlanOut)
async def switch_plan(
    payload: PlanSwitchRequest,
    current_user: Annotated[User, Depends(require_role(UserRole.B2B))],
    db: AsyncSession = Depends(get_db),
):
    user, _ = await service.switch_plan(db, current_user, payload.plan_id, payload.billing_cycle)
    return service.get_my_plan(user)


@router.get("/plans/history", response_model=PlanPurchaseListOut)
async def plan_history(
    current_user: Annotated[User, Depends(require_role(UserRole.B2B))],
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.list_history(db, current_user, page, page_size)
    return PlanPurchaseListOut(items=items, total=total, page=page, page_size=page_size)
