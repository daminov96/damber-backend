from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.modules.plans.catalog import PLAN_CATALOG, PlanDefinition, PlanId, yearly_price
from app.modules.plans.models import PlanPurchase
from app.modules.plans.schemas import MyPlanOut, PlanOut
from app.modules.users.models import BillingCycle, User
from app.modules.wallet import service as wallet_service
from app.modules.wallet.models import WalletTxKind

PLAN_DAYS: dict[BillingCycle, int] = {BillingCycle.monthly: 30, BillingCycle.yearly: 365}


def _to_plan_out(definition: PlanDefinition) -> PlanOut:
    return PlanOut(
        id=definition.id,
        name=definition.name,
        price=definition.price,
        yearly_price=yearly_price(definition.price),
        listing_limit=definition.listing_limit,
        photo_limit=definition.photo_limit,
        video_limit=definition.video_limit,
        video_size_mb=definition.video_size_mb,
        badge=definition.badge,
        emblem=definition.emblem,
        features=definition.features,
    )


def _effective_plan_id(user: User, today: date) -> PlanId:
    if user.current_plan_id and user.current_plan_id != PlanId.free.value:
        if user.plan_until and user.plan_until >= today:
            return PlanId(user.current_plan_id)
    return PlanId.free


def get_catalog() -> list[PlanOut]:
    return [_to_plan_out(definition) for definition in PLAN_CATALOG.values()]


def get_my_plan(user: User) -> MyPlanOut:
    today = date.today()
    effective_id = _effective_plan_id(user, today)
    days_left = max(0, (user.plan_until - today).days) if user.plan_until else 0
    return MyPlanOut(
        current_plan_id=effective_id,
        plan=_to_plan_out(PLAN_CATALOG[effective_id]),
        plan_until=user.plan_until,
        plan_period=user.plan_period,
        plan_rate=float(user.plan_rate) if user.plan_rate is not None else None,
        days_left=days_left,
    )


async def switch_plan(
    db: AsyncSession, user: User, plan_id: PlanId, billing_cycle: BillingCycle
) -> tuple[User, PlanPurchase]:
    if plan_id == PlanId.free:
        raise ConflictError("Bepul tarifni sotib olib bo'lmaydi — bu standart holat")

    definition = PLAN_CATALOG[plan_id]
    cost = (
        yearly_price(definition.price)
        if billing_cycle == BillingCycle.yearly
        else definition.price
    )
    today = date.today()

    has_active_plan = (
        user.current_plan_id is not None
        and user.current_plan_id != PlanId.free.value
        and user.plan_until is not None
        and user.plan_until >= today
    )
    days_left = max(0, (user.plan_until - today).days) if has_active_plan else 0
    rate = float(user.plan_rate or 0)
    days_added = PLAN_DAYS[billing_cycle]
    is_same_plan = has_active_plan and plan_id.value == user.current_plan_id
    mode = "new" if not has_active_plan else ("extend" if is_same_plan else "switch")

    refundable = round(rate * days_left) if has_active_plan else 0
    refund = refundable if mode == "switch" else 0
    new_rate = (
        (refundable + cost) / (days_left + days_added)
        if mode == "extend" and days_left > 0
        else cost / days_added
    )
    base_date = user.plan_until if mode == "extend" and user.plan_until else today
    new_until = base_date + timedelta(days=days_added)

    # Qaytim avval hamyonga tushadi, keyin TO'LIQ narx (payable emas!) yechiladi —
    # `wallet_service.pay()`ning balans tekshiruvi shu bilan qaytim hisobga olingan
    # holda ishlaydi (balans_avval + refund >= cost). Ikkalasi alohida ledger yozuvi.
    if refund > 0:
        await wallet_service.credit(
            db,
            user,
            refund,
            f"Tarif almashtirildi — {days_left} kun qaytarildi",
            kind=WalletTxKind.plan,
            ref=plan_id.value,
        )
    if cost > 0:
        label = "Tarif uzaytirildi" if mode == "extend" else "Tarif sotib olindi"
        await wallet_service.pay(
            db,
            user,
            cost,
            f"{label} — {definition.name}",
            kind=WalletTxKind.plan,
            ref=plan_id.value,
        )

    user.current_plan_id = plan_id.value
    user.plan_until = new_until
    user.plan_period = billing_cycle
    user.plan_rate = new_rate
    purchase = PlanPurchase(
        user_id=user.id, plan_id=plan_id, billing_cycle=billing_cycle, price_paid=cost
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
