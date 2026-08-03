from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


async def _topup(client: AsyncClient, headers: dict, amount: float) -> None:
    resp = await client.post("/api/v1/wallet/topup", json={"amount": amount}, headers=headers)
    assert resp.status_code == 200, resp.text


class TestCatalog:
    async def test_list_plans_has_four_tiers_with_correct_yearly_price(
        self, client: AsyncClient
    ):
        resp = await client.get("/api/v1/plans")
        assert resp.status_code == 200, resp.text
        items = {item["id"]: item for item in resp.json()["items"]}
        assert set(items) == {"free", "standard", "business", "premium"}

        business = items["business"]
        assert business["price"] == 300_000
        assert business["yearly_price"] == round(300_000 * 12 * 0.84)
        assert business["badge"] == "Tavsiya etamiz"
        assert business["emblem"] == "TOP"
        assert business["listing_limit"] == 7

        free = items["free"]
        assert free["price"] == 0
        assert free["yearly_price"] == 0
        assert free["listing_limit"] == 1


class TestMyPlan:
    async def test_new_b2b_user_defaults_to_free(self, client: AsyncClient, b2b_headers: dict):
        resp = await client.get("/api/v1/plans/mine", headers=b2b_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["current_plan_id"] == "free"
        assert body["plan"]["id"] == "free"
        assert body["plan_until"] is None
        assert body["plan_period"] is None
        assert body["plan_rate"] is None
        assert body["days_left"] == 0

    async def test_b2c_cannot_access(self, client: AsyncClient, b2c_headers: dict):
        resp = await client.get("/api/v1/plans/mine", headers=b2c_headers)
        assert resp.status_code == 403


class TestSwitchPlan:
    async def test_switch_to_paid_plan_debits_wallet_and_updates_current_plan(
        self, client: AsyncClient, b2b_headers: dict
    ):
        await _topup(client, b2b_headers, 1_000_000)

        resp = await client.post(
            "/api/v1/plans/switch",
            json={"plan_id": "business", "billing_cycle": "monthly"},
            headers=b2b_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["current_plan_id"] == "business"

        balance_resp = await client.get("/api/v1/wallet/balance", headers=b2b_headers)
        assert balance_resp.json()["balance"] == 1_000_000 - 300_000

        tx_resp = await client.get("/api/v1/wallet/transactions", headers=b2b_headers)
        kinds = [tx["kind"] for tx in tx_resp.json()["items"]]
        assert "plan" in kinds

    async def test_switch_with_insufficient_balance_returns_409_and_no_side_effects(
        self, client: AsyncClient, b2b_headers: dict
    ):
        resp = await client.post(
            "/api/v1/plans/switch",
            json={"plan_id": "premium", "billing_cycle": "monthly"},
            headers=b2b_headers,
        )
        assert resp.status_code == 409

        my_plan_resp = await client.get("/api/v1/plans/mine", headers=b2b_headers)
        assert my_plan_resp.json()["current_plan_id"] == "free"

        balance_resp = await client.get("/api/v1/wallet/balance", headers=b2b_headers)
        assert balance_resp.json()["balance"] == 0

    async def test_cannot_switch_to_free_plan(self, client: AsyncClient, b2b_headers: dict):
        resp = await client.post(
            "/api/v1/plans/switch", json={"plan_id": "free"}, headers=b2b_headers
        )
        assert resp.status_code == 409

    async def test_reselecting_same_active_plan_extends_without_refund(
        self, client: AsyncClient, b2b_headers: dict
    ):
        await _topup(client, b2b_headers, 1_000_000)
        first = await client.post(
            "/api/v1/plans/switch",
            json={"plan_id": "standard", "billing_cycle": "monthly"},
            headers=b2b_headers,
        )
        first_until = first.json()["plan_until"]

        second = await client.post(
            "/api/v1/plans/switch",
            json={"plan_id": "standard", "billing_cycle": "monthly"},
            headers=b2b_headers,
        )
        assert second.status_code == 200, second.text
        assert second.json()["current_plan_id"] == "standard"
        # Uzaytirishda muddat mavjud tugash sanasidan +30 kun (bugundan emas)
        assert second.json()["plan_until"] == str(
            date.fromisoformat(first_until) + timedelta(days=30)
        )

        balance_resp = await client.get("/api/v1/wallet/balance", headers=b2b_headers)
        # Ikkala xarid ham to'liq narxda yechilgan — uzaytirishda qaytim yo'q
        assert balance_resp.json()["balance"] == 1_000_000 - 150_000 - 150_000

    async def test_switching_between_paid_plans_refunds_prorated_remainder(
        self, client: AsyncClient, b2b_headers: dict
    ):
        await _topup(client, b2b_headers, 2_000_000)
        await client.post(
            "/api/v1/plans/switch",
            json={"plan_id": "standard", "billing_cycle": "monthly"},
            headers=b2b_headers,
        )
        balance_after_first = (
            await client.get("/api/v1/wallet/balance", headers=b2b_headers)
        ).json()["balance"]

        switch_resp = await client.post(
            "/api/v1/plans/switch",
            json={"plan_id": "business", "billing_cycle": "monthly"},
            headers=b2b_headers,
        )
        assert switch_resp.status_code == 200, switch_resp.text
        assert switch_resp.json()["current_plan_id"] == "business"
        # Standart 30 kunga 150000 to'lagan, hali hech kuni o'tmagan — rate = 150000/30 = 5000/kun,
        # 30 kun qolgan bo'lsa refundable ~150000 (round natijasida aynan shu)
        expected_refund = round((150_000 / 30) * 30)
        balance_after_switch = (
            await client.get("/api/v1/wallet/balance", headers=b2b_headers)
        ).json()["balance"]
        assert balance_after_switch == balance_after_first + expected_refund - 300_000

        tx_resp = await client.get("/api/v1/wallet/transactions", headers=b2b_headers)
        plan_txs = [tx for tx in tx_resp.json()["items"] if tx["kind"] == "plan"]
        assert len(plan_txs) >= 3  # standart xarid + qaytim + biznes xarid

    async def test_expired_plan_treated_as_new_purchase(
        self, client: AsyncClient, b2b_headers: dict, b2b_user: User, db_session: AsyncSession
    ):
        await _topup(client, b2b_headers, 1_000_000)
        await client.post(
            "/api/v1/plans/switch",
            json={"plan_id": "standard", "billing_cycle": "monthly"},
            headers=b2b_headers,
        )

        # Muddatni "o'tkazib yuborish" — bevosita DB orqali
        await db_session.refresh(b2b_user)
        b2b_user.plan_until = date.today() - timedelta(days=1)
        await db_session.commit()

        my_plan_resp = await client.get("/api/v1/plans/mine", headers=b2b_headers)
        assert my_plan_resp.json()["current_plan_id"] == "free"

        balance_before = (
            await client.get("/api/v1/wallet/balance", headers=b2b_headers)
        ).json()["balance"]

        switch_resp = await client.post(
            "/api/v1/plans/switch",
            json={"plan_id": "business", "billing_cycle": "monthly"},
            headers=b2b_headers,
        )
        assert switch_resp.status_code == 200, switch_resp.text
        # Muddati o'tgan tarif uchun qaytim yo'q (mode=new) — to'liq narx yechiladi
        balance_after = (
            await client.get("/api/v1/wallet/balance", headers=b2b_headers)
        ).json()["balance"]
        assert balance_after == balance_before - 300_000

    async def test_yearly_billing_cycle_charges_discounted_price(
        self, client: AsyncClient, b2b_headers: dict
    ):
        await _topup(client, b2b_headers, 2_000_000)

        resp = await client.post(
            "/api/v1/plans/switch",
            json={"plan_id": "standard", "billing_cycle": "yearly"},
            headers=b2b_headers,
        )
        assert resp.status_code == 200, resp.text

        expected_price = round(150_000 * 12 * 0.84)
        balance_resp = await client.get("/api/v1/wallet/balance", headers=b2b_headers)
        assert balance_resp.json()["balance"] == 2_000_000 - expected_price

    async def test_invalid_plan_id_returns_422(self, client: AsyncClient, b2b_headers: dict):
        resp = await client.post(
            "/api/v1/plans/switch", json={"plan_id": "vip999"}, headers=b2b_headers
        )
        assert resp.status_code == 422

    async def test_b2c_cannot_switch(self, client: AsyncClient, b2c_headers: dict):
        resp = await client.post(
            "/api/v1/plans/switch", json={"plan_id": "standard"}, headers=b2c_headers
        )
        assert resp.status_code == 403


class TestPlanHistory:
    async def test_history_lists_only_own_purchases(
        self, client: AsyncClient, b2b_headers: dict
    ):
        await _topup(client, b2b_headers, 1_000_000)
        await client.post(
            "/api/v1/plans/switch", json={"plan_id": "standard"}, headers=b2b_headers
        )

        resp = await client.get("/api/v1/plans/history", headers=b2b_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["plan_id"] == "standard"
        assert body["items"][0]["price_paid"] == 150_000

    async def test_b2c_cannot_access_history(self, client: AsyncClient, b2c_headers: dict):
        resp = await client.get("/api/v1/plans/history", headers=b2c_headers)
        assert resp.status_code == 403
