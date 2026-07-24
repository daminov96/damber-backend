import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.wallet.models import WalletTxKind, WalletTxStatus


class TopupRequest(BaseModel):
    amount: float = Field(gt=0)
    method: str | None = None


class WalletBalanceOut(BaseModel):
    balance: float


class WalletTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    amount: float
    status: WalletTxStatus
    kind: WalletTxKind | None
    method: str | None
    ref: str | None
    created_at: datetime


class WalletTransactionListOut(BaseModel):
    items: list[WalletTransactionOut]
    total: int
    page: int
    page_size: int
