import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class WalletTxKind(enum.StrEnum):
    topup = "topup"
    promo = "promo"
    booking = "booking"
    refund = "refund"
    other = "other"


class WalletTxStatus(enum.StrEnum):
    success = "success"
    pending = "pending"


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)

    label: Mapped[str] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    status: Mapped[WalletTxStatus] = mapped_column(
        Enum(WalletTxStatus, name="wallet_tx_status"), default=WalletTxStatus.success
    )
    kind: Mapped[WalletTxKind | None] = mapped_column(
        Enum(WalletTxKind, name="wallet_tx_kind"), nullable=True
    )
    method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ref: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
