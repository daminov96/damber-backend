from httpx import AsyncClient

from app.core.security import create_token


async def _register(client: AsyncClient, phone: str, role: str = "B2C", **overrides) -> dict:
    payload = {
        "name": "Test",
        "surname": "User",
        "phone": phone,
        "password": "password123",
        "role": role,
        **overrides,
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestRegister:
    async def test_register_returns_token_pair(self, client: AsyncClient):
        body = await _register(client, "998911100001")
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_duplicate_phone_returns_409(self, client: AsyncClient):
        await _register(client, "998911100002")
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Boshqa",
                "surname": "User",
                "phone": "998911100002",
                "password": "password123",
                "role": "B2C",
            },
        )
        assert resp.status_code == 409

    async def test_me_reflects_biz_category(self, client: AsyncClient):
        body = await _register(
            client, "998911100003", role="B2B", biz_category="Dala hovli / Kurort"
        )
        headers = {"Authorization": f"Bearer {body['access_token']}"}
        me_resp = await client.get("/api/v1/users/me", headers=headers)
        assert me_resp.status_code == 200, me_resp.text
        assert me_resp.json()["biz_category"] == "Dala hovli / Kurort"


class TestLogin:
    async def test_login_with_correct_password(self, client: AsyncClient):
        await _register(client, "998911100004")
        resp = await client.post(
            "/api/v1/auth/login",
            json={"identifier": "998911100004", "password": "password123"},
        )
        assert resp.status_code == 200, resp.text
        assert "access_token" in resp.json()

    async def test_login_with_wrong_password_returns_401(self, client: AsyncClient):
        await _register(client, "998911100005")
        resp = await client.post(
            "/api/v1/auth/login",
            json={"identifier": "998911100005", "password": "wrongpass"},
        )
        assert resp.status_code == 401


class TestRefresh:
    async def test_refresh_issues_new_working_token_pair(self, client: AsyncClient):
        register_body = await _register(client, "998911100006")

        refresh_resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": register_body["refresh_token"]}
        )
        assert refresh_resp.status_code == 200, refresh_resp.text
        new_tokens = refresh_resp.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens

        me_resp = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        )
        assert me_resp.status_code == 200, me_resp.text

    async def test_refresh_rejects_access_token(self, client: AsyncClient):
        register_body = await _register(client, "998911100007")

        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": register_body["access_token"]}
        )
        assert resp.status_code == 401

    async def test_refresh_rejects_garbage_token(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"}
        )
        assert resp.status_code == 401

    async def test_refresh_rejects_banned_user(self, client: AsyncClient, admin_headers: dict):
        register_body = await _register(client, "998911100008")

        me_resp = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {register_body['access_token']}"},
        )
        user_id = me_resp.json()["id"]

        await client.post(
            f"/api/v1/admin/users/{user_id}/ban",
            json={"reason": "test"},
            headers=admin_headers,
        )

        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": register_body["refresh_token"]}
        )
        assert resp.status_code == 401

    async def test_refresh_with_nonexistent_user_returns_401(self, client: AsyncClient):
        # yaroqli imzo/tur, lekin bunday foydalanuvchi DB'da yo'q
        token = create_token("00000000-0000-0000-0000-000000000000", "refresh")
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": token})
        assert resp.status_code == 401
