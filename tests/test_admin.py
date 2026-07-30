from httpx import AsyncClient


async def _register(client: AsyncClient, phone: str, role: str = "B2C") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "Test",
            "surname": "User",
            "phone": phone,
            "password": "password123",
            "role": role,
        },
    )
    return resp


async def _register_and_get_user(client: AsyncClient, phone: str, role: str = "B2C") -> dict:
    resp = await _register(client, phone, role)
    assert resp.status_code == 200, resp.text
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    me_resp = await client.get("/api/v1/users/me", headers=headers)
    assert me_resp.status_code == 200, me_resp.text
    return {"user": me_resp.json(), "headers": headers}


class TestRegistrationSecurity:
    async def test_cannot_self_register_as_admin(self, client: AsyncClient):
        resp = await _register(client, "998922200001", role="ADMIN")
        assert resp.status_code == 422


class TestAdminAccessControl:
    async def test_non_admin_cannot_access_dashboard(self, client: AsyncClient, b2c_headers: dict):
        resp = await client.get("/api/v1/admin/dashboard", headers=b2c_headers)
        assert resp.status_code == 403

    async def test_non_admin_cannot_list_users(self, client: AsyncClient, b2b_headers: dict):
        resp = await client.get("/api/v1/admin/users", headers=b2b_headers)
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_access_admin_routes(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/dashboard")
        assert resp.status_code == 401


class TestInviteAdmin:
    async def test_invite_admin_creates_working_admin_account(
        self, client: AsyncClient, admin_headers: dict
    ):
        resp = await client.post(
            "/api/v1/admin/users/invite-admin",
            json={
                "name": "Yangi",
                "surname": "Admin",
                "phone": "998922200002",
                "password": "password123",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["role"] == "ADMIN"

        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"identifier": "998922200002", "password": "password123"},
        )
        assert login_resp.status_code == 200, login_resp.text

    async def test_non_admin_cannot_invite_admin(self, client: AsyncClient, b2b_headers: dict):
        resp = await client.post(
            "/api/v1/admin/users/invite-admin",
            json={
                "name": "Yangi",
                "surname": "Admin",
                "phone": "998922200003",
                "password": "password123",
            },
            headers=b2b_headers,
        )
        assert resp.status_code == 403


class TestBanUnban:
    async def test_ban_blocks_login_and_existing_token(
        self, client: AsyncClient, admin_headers: dict
    ):
        registered = await _register_and_get_user(client, "998922200004", role="B2C")
        user_id = registered["user"]["id"]
        user_headers = registered["headers"]

        ban_resp = await client.post(
            f"/api/v1/admin/users/{user_id}/ban",
            json={"reason": "Qoidabuzarlik"},
            headers=admin_headers,
        )
        assert ban_resp.status_code == 200, ban_resp.text
        assert ban_resp.json()["is_banned"] is True

        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"identifier": "998922200004", "password": "password123"},
        )
        assert login_resp.status_code == 403

        me_resp = await client.get("/api/v1/users/me", headers=user_headers)
        assert me_resp.status_code == 403

    async def test_unban_restores_access(self, client: AsyncClient, admin_headers: dict):
        registered = await _register_and_get_user(client, "998922200005", role="B2C")
        user_id = registered["user"]["id"]

        await client.post(
            f"/api/v1/admin/users/{user_id}/ban",
            json={"reason": "Sabab"},
            headers=admin_headers,
        )
        unban_resp = await client.post(
            f"/api/v1/admin/users/{user_id}/unban", headers=admin_headers
        )
        assert unban_resp.status_code == 200
        assert unban_resp.json()["is_banned"] is False

        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"identifier": "998922200005", "password": "password123"},
        )
        assert login_resp.status_code == 200

    async def test_cannot_ban_another_admin(
        self, client: AsyncClient, admin_headers: dict, admin_user
    ):
        invite_resp = await client.post(
            "/api/v1/admin/users/invite-admin",
            json={
                "name": "Ikkinchi",
                "surname": "Admin",
                "phone": "998922200006",
                "password": "password123",
            },
            headers=admin_headers,
        )
        other_admin_id = invite_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/admin/users/{other_admin_id}/ban",
            json={"reason": "Sabab"},
            headers=admin_headers,
        )
        assert resp.status_code == 403


class TestDashboardAndAuditLog:
    async def test_dashboard_reflects_real_counts(self, client: AsyncClient, admin_headers: dict):
        await _register(client, "998922200007", role="B2C")
        await _register(client, "998922200008", role="B2B")

        resp = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["users_total"] >= 3
        assert body["users_by_role"]["B2C"] >= 1
        assert body["users_by_role"]["B2B"] >= 1

    async def test_audit_log_records_admin_actions(self, client: AsyncClient, admin_headers: dict):
        registered = await _register_and_get_user(client, "998922200009", role="B2C")
        user_id = registered["user"]["id"]

        await client.post(
            f"/api/v1/admin/users/{user_id}/ban",
            json={"reason": "Test sabab"},
            headers=admin_headers,
        )

        resp = await client.get(
            "/api/v1/admin/audit-log", params={"action": "user_ban"}, headers=admin_headers
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] >= 1
        assert body["items"][0]["action"] == "user_ban"
        assert body["items"][0]["target_id"] == user_id


class TestUserListing:
    async def test_filters_by_role_and_query(self, client: AsyncClient, admin_headers: dict):
        await _register(client, "998922200010", role="B2C")

        resp = await client.get(
            "/api/v1/admin/users", params={"role": "B2C", "query": "998922200010"},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert any(u["phone"] == "998922200010" for u in body["items"])
