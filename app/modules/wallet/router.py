from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.modules.wallet import service
from app.modules.wallet.schemas import (
    TopupRequest,
    WalletBalanceOut,
    WalletTransactionListOut,
    WalletTransactionOut,
)

router = APIRouter(prefix="/api/v1", tags=["wallet"])


@router.get("/wallet/balance", response_model=WalletBalanceOut)
async def get_wallet_balance(current_user: CurrentUser):
    return WalletBalanceOut(balance=service.get_balance(current_user))


@router.get("/wallet/transactions", response_model=WalletTransactionListOut)
async def get_wallet_transactions(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.list_transactions(db, current_user, page, page_size)
    return WalletTransactionListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/wallet/topup", response_model=WalletTransactionOut)
async def topup_wallet(
    payload: TopupRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.topup(db, current_user, payload.amount, payload.method)
