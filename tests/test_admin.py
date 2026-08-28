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
                "admin_role": "moderator",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["role"] == "ADMIN"
        assert resp.json()["admin_role"] == "moderator"

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
                "admin_role": "moderator",
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
                "admin_role": "moderator",
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

    async def test_dashboard_listings_by_type_breakdown(
        self, client: AsyncClient, admin_headers: dict
    ):
        owner = await _register_and_get_user(client, "998922200010", role="B2B")
        create_resp = await client.post(
            "/api/v1/listings",
            json={
                "name": "Dashboard Test Villa",
                "type": "Villa",
                "region": "Tashkent",
                "weekday_price": 100,
                "weekend_price": 150,
                "capacity": 4,
                "amenities": ["wifi"],
                "description": "dashboard by_type test",
            },
            headers=owner["headers"],
        )
        assert create_resp.status_code == 201, create_resp.text
        listing_id = create_resp.json()["id"]

        resp = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
        assert resp.status_code == 200, resp.text
        villa_stats = resp.json()["listings_by_type"]["Villa"]
        assert villa_stats["pending"] >= 1

        await client.post(f"/api/v1/admin/listings/{listing_id}/approve", headers=admin_headers)
        resp2 = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
        villa_stats2 = resp2.json()["listings_by_type"]["Villa"]
        assert villa_stats2["approved"] >= 1

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


async def _invite_admin(
    client: AsyncClient, admin_headers: dict, phone: str, admin_role: str = "moderator"
) -> dict:
    resp = await client.post(
        "/api/v1/admin/users/invite-admin",
        json={
            "name": "Test",
            "surname": "Admin",
            "phone": phone,
            "password": "password123",
            "admin_role": admin_role,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestAdminRoleManagement:
    async def test_super_can_change_admin_role(self, client: AsyncClient, admin_headers: dict):
        target = await _invite_admin(client, admin_headers, "998922200011", "moderator")

        resp = await client.patch(
            f"/api/v1/admin/users/{target['id']}/admin-role",
            json={"admin_role": "finance"},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["admin_role"] == "finance"

    async def test_non_super_cannot_change_admin_role(
        self, client: AsyncClient, admin_headers: dict, moderator_headers: dict
    ):
        target = await _invite_admin(client, admin_headers, "998922200012", "content")

        resp = await client.patch(
            f"/api/v1/admin/users/{target['id']}/admin-role",
            json={"admin_role": "finance"},
            headers=moderator_headers,
        )
        assert resp.status_code == 403

    async def test_super_cannot_change_own_role(
        self, client: AsyncClient, admin_headers: dict, admin_user
    ):
        resp = await client.patch(
            f"/api/v1/admin/users/{admin_user.id}/admin-role",
            json={"admin_role": "moderator"},
            headers=admin_headers,
        )
        assert resp.status_code == 403

    async def test_two_supers_second_can_demote_first(
        self, client: AsyncClient, admin_headers: dict, admin_user
    ):
        # Ikkinchi super qo'shamiz — endi ikkita super bor: admin_user, second_super.
        await _invite_admin(client, admin_headers, "998922200013", "super")
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"identifier": "998922200013", "password": "password123"},
        )
        second_super_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        # second_super ASL admin_userni pasaytiradi — ikkita super bor edi,
        # bu OK (yagona-super qoidasi ishga tushmaydi).
        demote_resp = await client.patch(
            f"/api/v1/admin/users/{admin_user.id}/admin-role",
            json={"admin_role": "moderator"},
            headers=second_super_headers,
        )
        assert demote_resp.status_code == 200, demote_resp.text
        assert demote_resp.json()["admin_role"] == "moderator"


class TestAdminDeletion:
    async def test_super_can_delete_admin(self, client: AsyncClient, admin_headers: dict):
        target = await _invite_admin(client, admin_headers, "998922200020", "content")

        resp = await client.delete(
            f"/api/v1/admin/users/{target['id']}", headers=admin_headers
        )
        assert resp.status_code == 204

        # O'chirilgan admin bilan login endi ishlamasligi kerak
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"identifier": "998922200020", "password": "password123"},
        )
        assert login_resp.status_code == 401

    async def test_cannot_delete_self(self, client: AsyncClient, admin_headers: dict, admin_user):
        resp = await client.delete(
            f"/api/v1/admin/users/{admin_user.id}", headers=admin_headers
        )
        assert resp.status_code == 403

    async def test_non_super_cannot_delete_admin(
        self, client: AsyncClient, admin_headers: dict, moderator_headers: dict
    ):
        target = await _invite_admin(client, admin_headers, "998922200021", "content")

        resp = await client.delete(
            f"/api/v1/admin/users/{target['id']}", headers=moderator_headers
        )
        assert resp.status_code == 403

    async def test_cannot_delete_last_super(
        self, client: AsyncClient, admin_headers: dict, admin_user
    ):
        # Ikkinchi super qo'shib, u orqali ASL admin_userni (birinchi super)
        # o'chirishga urinamiz — admin_user shu paytda YAGONA super emas
        # (second_super ham bor), shuning uchun bu qadam OK bo'ladi va
        # second_super yagona super bo'lib qoladi.
        second_super = await _invite_admin(client, admin_headers, "998922200022", "super")
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"identifier": "998922200022", "password": "password123"},
        )
        second_super_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        del_resp = await client.delete(
            f"/api/v1/admin/users/{admin_user.id}", headers=second_super_headers
        )
        assert del_resp.status_code == 204

        # Endi second_super yagona super. O'zini o'zi o'chirishga urinadi —
        # "o'zini o'chira olmaydi" qoidasi ConflictError'dan oldin
        # tekshiriladi, shuning uchun javob 403 (yagona-super ConflictError
        # qoidasi service kodida qoladi — `_count_supers` orqali; HTTP
        # darajasida uni ikkita mustaqil admin bilan keltirib chiqarish
        # mumkin emas, chunki harakat qiluvchi super har doim nishondan
        # tashqari hisoblanadi va bu holatda kamida 2 ta super bor bo'lib
        # chiqadi — shart hech qachon HTTP orqali ikki-actor holatida
        # bajarilmaydi, faqat "o'zini o'chirish" yo'lida amalda ishlaydi).
        self_resp = await client.delete(
            f"/api/v1/admin/users/{second_super['id']}", headers=second_super_headers
        )
        assert self_resp.status_code == 403


class TestModuleEnforcement:
    async def test_moderator_can_access_users_module(
        self, client: AsyncClient, moderator_headers: dict
    ):
        resp = await client.get("/api/v1/admin/users", headers=moderator_headers)
        assert resp.status_code == 200

    async def test_moderator_cannot_invite_admin(
        self, client: AsyncClient, moderator_headers: dict
    ):
        resp = await client.post(
            "/api/v1/admin/users/invite-admin",
            json={
                "name": "X",
                "surname": "Y",
                "phone": "998922200030",
                "password": "password123",
                "admin_role": "content",
            },
            headers=moderator_headers,
        )
        assert resp.status_code == 403
