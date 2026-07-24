import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.users.models import User
from app.modules.wallet.models import WalletTransaction, WalletTxKind, WalletTxStatus


async def _lock_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    stmt = select(User).where(User.id == user_id).with_for_update()
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Foydalanuvchi topilmadi")
    return user


def get_balance(user: User) -> float:
    return user.wallet_balance


async def list_transactions(
    db: AsyncSession, user: User, page: int, page_size: int
) -> tuple[list[WalletTransaction], int]:
    count_stmt = (
        select(func.count())
        .select_from(WalletTransaction)
        .where(WalletTransaction.user_id == user.id)
    )
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(WalletTransaction)
        .where(WalletTransaction.user_id == user.id)
        .order_by(WalletTransaction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def topup(
    db: AsyncSession, user: User, amount: float, method: str | None
) -> WalletTransaction:
    locked_user = await _lock_user(db, user.id)
    amount = round(amount, 2)
    locked_user.wallet_balance = round(float(locked_user.wallet_balance) + amount, 2)
    tx = WalletTransaction(
        user_id=locked_user.id,
        label="Hisobni to'ldirish",
        amount=amount,
        status=WalletTxStatus.success,
        kind=WalletTxKind.topup,
        method=method,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx


async def pay(
    db: AsyncSession,
    user: User,
    amount: float,
    label: str,
    kind: WalletTxKind = WalletTxKind.other,
    ref: str | None = None,
) -> WalletTransaction:
    locked_user = await _lock_user(db, user.id)
    amount = round(amount, 2)
    if float(locked_user.wallet_balance) < amount:
        raise ConflictError("Balansda mablag' yetarli emas")
    locked_user.wallet_balance = round(float(locked_user.wallet_balance) - amount, 2)
    tx = WalletTransaction(
        user_id=locked_user.id,
        label=label,
        amount=-amount,
        status=WalletTxStatus.success,
        kind=kind,
        ref=ref,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx


async def transfer(
    db: AsyncSession,
    from_user: User,
    to_user: User,
    amount: float,
    label: str,
    kind: WalletTxKind = WalletTxKind.other,
    ref: str | None = None,
) -> tuple[WalletTransaction, WalletTransaction]:
    """Faqat ichki chaqiruv uchun (masalan Bookings escrow) — public endpoint yo'q."""
    debit_tx = await pay(db, from_user, amount, label, kind=kind, ref=ref)

    locked_to_user = await _lock_user(db, to_user.id)
    amount = round(amount, 2)
    locked_to_user.wallet_balance = round(float(locked_to_user.wallet_balance) + amount, 2)
    credit_tx = WalletTransaction(
        user_id=locked_to_user.id,
        label=label,
        amount=amount,
        status=WalletTxStatus.success,
        kind=kind,
        ref=ref,
    )
    db.add(credit_tx)
    await db.commit()
    await db.refresh(credit_tx)
    return debit_tx, credit_tx
