from httpx import AsyncClient

LISTING_PAYLOAD = {
    "name": "Chat Test Dacha",
    "type": "Dacha",
    "region": "Tashkent",
    "weekday_price": 100,
    "weekend_price": 150,
    "capacity": 4,
    "amenities": ["wifi"],
    "description": "chat test uchun listing",
}


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
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_listing(client: AsyncClient, owner_headers: dict, **overrides) -> dict:
    payload = {**LISTING_PAYLOAD, **overrides}
    resp = await client.post("/api/v1/listings", json=payload, headers=owner_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _start_conversation(client: AsyncClient, client_headers: dict, listing_id: str) -> dict:
    resp = await client.post(
        "/api/v1/chat/conversations", json={"listing_id": listing_id}, headers=client_headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestStartConversation:
    async def test_creates_new_conversation(self, client: AsyncClient, b2b_headers: dict):
        owner_headers = b2b_headers
        listing = await _create_listing(client, owner_headers)
        guest_headers = await _register(client, "998933300001", role="B2C")

        conversation = await _start_conversation(client, guest_headers, listing["id"])
        assert conversation["listing_id"] == listing["id"]
        assert conversation["unread_count"] == 0
        assert conversation["last_message"] is None

    async def test_idempotent_for_same_client_and_owner(
        self, client: AsyncClient, b2b_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers)
        guest_headers = await _register(client, "998933300002", role="B2C")

        first = await _start_conversation(client, guest_headers, listing["id"])
        second = await _start_conversation(client, guest_headers, listing["id"])
        assert first["id"] == second["id"]

    async def test_second_listing_same_owner_reuses_conversation(
        self, client: AsyncClient, b2b_headers: dict
    ):
        listing_a = await _create_listing(client, b2b_headers, name="Listing A")
        listing_b = await _create_listing(client, b2b_headers, name="Listing B")
        guest_headers = await _register(client, "998933300003", role="B2C")

        first = await _start_conversation(client, guest_headers, listing_a["id"])
        second = await _start_conversation(client, guest_headers, listing_b["id"])
        assert first["id"] == second["id"]

    async def test_cannot_message_own_listing(self, client: AsyncClient, b2b_headers: dict):
        listing = await _create_listing(client, b2b_headers)

        resp = await client.post(
            "/api/v1/chat/conversations", json={"listing_id": listing["id"]}, headers=b2b_headers
        )
        assert resp.status_code == 409


class TestMessaging:
    async def test_send_and_read_messages(self, client: AsyncClient, b2b_headers: dict):
        listing = await _create_listing(client, b2b_headers)
        guest_headers = await _register(client, "998933300004", role="B2C")
        conversation = await _start_conversation(client, guest_headers, listing["id"])

        send_resp = await client.post(
            f"/api/v1/chat/conversations/{conversation['id']}/messages",
            json={"text": "15-iyulga joy bormi?"},
            headers=guest_headers,
        )
        assert send_resp.status_code == 201, send_resp.text
        assert send_resp.json()["text"] == "15-iyulga joy bormi?"

        messages_resp = await client.get(
            f"/api/v1/chat/conversations/{conversation['id']}/messages", headers=b2b_headers
        )
        assert messages_resp.status_code == 200
        body = messages_resp.json()
        assert body["total"] == 1
        assert body["items"][0]["text"] == "15-iyulga joy bormi?"

    async def test_stranger_cannot_access_conversation(
        self, client: AsyncClient, b2b_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers)
        guest_headers = await _register(client, "998933300005", role="B2C")
        conversation = await _start_conversation(client, guest_headers, listing["id"])

        stranger_headers = await _register(client, "998933300006", role="B2C")

        get_resp = await client.get(
            f"/api/v1/chat/conversations/{conversation['id']}/messages", headers=stranger_headers
        )
        assert get_resp.status_code == 403

        send_resp = await client.post(
            f"/api/v1/chat/conversations/{conversation['id']}/messages",
            json={"text": "Salom"},
            headers=stranger_headers,
        )
        assert send_resp.status_code == 403

    async def test_sensitive_data_blocked(self, client: AsyncClient, b2b_headers: dict):
        listing = await _create_listing(client, b2b_headers)
        guest_headers = await _register(client, "998933300007", role="B2C")
        conversation = await _start_conversation(client, guest_headers, listing["id"])

        resp = await client.post(
            f"/api/v1/chat/conversations/{conversation['id']}/messages",
            json={"text": "Menga shu raqamga qo'ng'iroq qiling: 998901234567"},
            headers=guest_headers,
        )
        assert resp.status_code == 400

    async def test_mark_read_clears_unread_count(self, client: AsyncClient, b2b_headers: dict):
        listing = await _create_listing(client, b2b_headers)
        guest_headers = await _register(client, "998933300008", role="B2C")
        conversation = await _start_conversation(client, guest_headers, listing["id"])

        await client.post(
            f"/api/v1/chat/conversations/{conversation['id']}/messages",
            json={"text": "Salom"},
            headers=guest_headers,
        )

        list_resp = await client.get("/api/v1/chat/conversations", headers=b2b_headers)
        items = list_resp.json()["items"]
        assert next(c for c in items if c["id"] == conversation["id"])["unread_count"] == 1

        read_resp = await client.post(
            f"/api/v1/chat/conversations/{conversation['id']}/read", headers=b2b_headers
        )
        assert read_resp.status_code == 204

        list_resp2 = await client.get("/api/v1/chat/conversations", headers=b2b_headers)
        items2 = list_resp2.json()["items"]
        assert next(c for c in items2 if c["id"] == conversation["id"])["unread_count"] == 0


class TestListConversations:
    async def test_visible_to_both_participants_with_last_message(
        self, client: AsyncClient, b2b_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers)
        guest_headers = await _register(client, "998933300009", role="B2C")
        conversation = await _start_conversation(client, guest_headers, listing["id"])

        await client.post(
            f"/api/v1/chat/conversations/{conversation['id']}/messages",
            json={"text": "Salom, bosh joy bormi?"},
            headers=guest_headers,
        )

        guest_list = await client.get("/api/v1/chat/conversations", headers=guest_headers)
        owner_list = await client.get("/api/v1/chat/conversations", headers=b2b_headers)

        assert any(c["id"] == conversation["id"] for c in guest_list.json()["items"])
        assert any(c["id"] == conversation["id"] for c in owner_list.json()["items"])

        owner_item = next(c for c in owner_list.json()["items"] if c["id"] == conversation["id"])
        assert owner_item["last_message"]["text"] == "Salom, bosh joy bormi?"
