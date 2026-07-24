import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.modules.users.models import User
from app.modules.wallet import service


class TestTopup:
    async def test_topup_increases_balance_and_creates_tx(
        self, client: AsyncClient, b2c_headers: dict
    ):
        resp = await client.post(
            "/api/v1/wallet/topup", json={"amount": 50000}, headers=b2c_headers
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["amount"] == 50000
        assert body["kind"] == "topup"
        assert body["status"] == "success"

        balance_resp = await client.get("/api/v1/wallet/balance", headers=b2c_headers)
        assert balance_resp.json()["balance"] == 50000


class TestBalanceAndHistory:
    async def test_get_balance_and_transactions(self, client: AsyncClient, b2c_headers: dict):
        await client.post("/api/v1/wallet/topup", json={"amount": 10000}, headers=b2c_headers)
        await client.post("/api/v1/wallet/topup", json={"amount": 5000}, headers=b2c_headers)

        balance_resp = await client.get("/api/v1/wallet/balance", headers=b2c_headers)
        assert balance_resp.json()["balance"] == 15000

        tx_resp = await client.get("/api/v1/wallet/transactions", headers=b2c_headers)
        body = tx_resp.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2


class TestPay:
    async def test_pay_with_sufficient_balance_succeeds(
        self, db_session: AsyncSession, b2c_user: User
    ):
        await service.topup(db_session, b2c_user, 10000, None)
        tx = await service.pay(db_session, b2c_user, 4000, "Test to'lov")
        assert tx.amount == -4000
        assert b2c_user.wallet_balance == 6000

    async def test_pay_with_insufficient_balance_raises_conflict(
        self, db_session: AsyncSession, b2c_user: User
    ):
        with pytest.raises(ConflictError):
            await service.pay(db_session, b2c_user, 100, "Test to'lov")
        assert b2c_user.wallet_balance == 0


class TestTransfer:
    async def test_transfer_updates_both_balances(
        self, db_session: AsyncSession, b2c_user: User, b2b_user: User
    ):
        await service.topup(db_session, b2c_user, 20000, None)

        debit_tx, credit_tx = await service.transfer(
            db_session, b2c_user, b2b_user, 15000, "Booking uchun to'lov"
        )
        assert debit_tx.amount == -15000
        assert credit_tx.amount == 15000
        assert b2c_user.wallet_balance == 5000
        assert b2b_user.wallet_balance == 15000
