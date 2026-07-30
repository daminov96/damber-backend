from httpx import AsyncClient


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

        free = items["free"]
        assert free["price"] == 0
        assert free["yearly_price"] == 0


class TestMyPlan:
    async def test_new_b2b_user_defaults_to_free(self, client: AsyncClient, b2b_headers: dict):
        resp = await client.get("/api/v1/plans/mine", headers=b2b_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["current_plan_id"] == "free"
        assert body["plan"]["id"] == "free"

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

    async def test_switch_to_free_does_not_touch_wallet(
        self, client: AsyncClient, b2b_headers: dict
    ):
        await _topup(client, b2b_headers, 1_000_000)
        await client.post(
            "/api/v1/plans/switch", json={"plan_id": "standard"}, headers=b2b_headers
        )
        balance_before = (
            await client.get("/api/v1/wallet/balance", headers=b2b_headers)
        ).json()["balance"]

        resp = await client.post(
            "/api/v1/plans/switch", json={"plan_id": "free"}, headers=b2b_headers
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["current_plan_id"] == "free"

        balance_after = (
            await client.get("/api/v1/wallet/balance", headers=b2b_headers)
        ).json()["balance"]
        assert balance_after == balance_before

    async def test_switch_to_current_plan_returns_409(
        self, client: AsyncClient, b2b_headers: dict
    ):
        resp = await client.post(
            "/api/v1/plans/switch", json={"plan_id": "free"}, headers=b2b_headers
        )
        assert resp.status_code == 409

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
