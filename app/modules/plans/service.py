from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.modules.plans.catalog import PLAN_CATALOG, PlanDefinition, PlanId, yearly_price
from app.modules.plans.models import BillingCycle, PlanPurchase
from app.modules.plans.schemas import MyPlanOut, PlanOut
from app.modules.users.models import User
from app.modules.wallet import service as wallet_service
from app.modules.wallet.models import WalletTxKind


def _to_plan_out(definition: PlanDefinition) -> PlanOut:
    return PlanOut(
        id=definition.id,
        name=definition.name,
        price=definition.price,
        yearly_price=yearly_price(definition.price),
        photo_limit=definition.photo_limit,
        video_limit=definition.video_limit,
        video_size_mb=definition.video_size_mb,
        badge=definition.badge,
        emblem=definition.emblem,
        features=definition.features,
    )


def _current_plan_id(user: User) -> PlanId:
    return PlanId(user.current_plan_id) if user.current_plan_id else PlanId.free


def get_catalog() -> list[PlanOut]:
    return [_to_plan_out(definition) for definition in PLAN_CATALOG.values()]


def get_my_plan(user: User) -> MyPlanOut:
    current_id = _current_plan_id(user)
    return MyPlanOut(current_plan_id=current_id, plan=_to_plan_out(PLAN_CATALOG[current_id]))


async def switch_plan(
    db: AsyncSession, user: User, plan_id: PlanId, billing_cycle: BillingCycle
) -> tuple[User, PlanPurchase]:
    if plan_id == _current_plan_id(user):
        raise ConflictError("Siz allaqachon shu tarifdasiz")

    definition = PLAN_CATALOG[plan_id]
    price = (
        yearly_price(definition.price)
        if billing_cycle == BillingCycle.yearly
        else definition.price
    )

    if price > 0:
        await wallet_service.pay(
            db,
            user,
            price,
            f"Tarif sotib olindi — {definition.name}",
            kind=WalletTxKind.plan,
            ref=plan_id.value,
        )

    user.current_plan_id = plan_id.value
    purchase = PlanPurchase(
        user_id=user.id, plan_id=plan_id, billing_cycle=billing_cycle, price_paid=price
    )
    db.add(purchase)
    await db.commit()
    await db.refresh(user)
    await db.refresh(purchase)
    return user, purchase


async def list_history(
    db: AsyncSession, user: User, page: int, page_size: int
) -> tuple[list[PlanPurchase], int]:
    count_stmt = (
        select(func.count()).select_from(PlanPurchase).where(PlanPurchase.user_id == user.id)
    )
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(PlanPurchase)
        .where(PlanPurchase.user_id == user.id)
        .order_by(PlanPurchase.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total
