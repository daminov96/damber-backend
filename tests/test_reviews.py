from datetime import date, timedelta

from httpx import AsyncClient

LISTING_PAYLOAD = {
    "name": "Test Dacha",
    "type": "Dacha",
    "region": "Tashkent",
    "weekday_price": 100_000,
    "weekend_price": 150_000,
    "capacity": 4,
    "amenities": [],
    "description": "Test tavsif",
}

OPERATOR_PAYLOAD = {
    "name": "Test Operator",
    "tin": "123456789",
    "license": "LIC-001",
    "license_expiry": "2030-01-01",
    "phone": "998911111111",
    "email": "operator@test.local",
    "office": "Toshkent, Chilonzor",
    "region": "Tashkent",
    "description": "Test tavsif",
}

TOUR_PAYLOAD = {
    "name": "Samarqand-Buxoro turi",
    "duration": "3 kun / 2 tun",
    "region": "Samarkand",
    "meeting_point": "Toshkent temir yo'l vokzali",
    "price": 500000,
    "description": "Test tur tavsifi",
}


def _next_monday() -> date:
    today = date.today()
    return today + timedelta(days=(7 - today.weekday()) % 7 or 7)


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


async def _create_listing(client: AsyncClient, b2b_headers: dict, admin_headers: dict) -> dict:
    resp = await client.post("/api/v1/listings", json=LISTING_PAYLOAD, headers=b2b_headers)
    assert resp.status_code == 201, resp.text
    listing = resp.json()
    approve_resp = await client.post(
        f"/api/v1/admin/listings/{listing['id']}/approve", headers=admin_headers
    )
    assert approve_resp.status_code == 200, approve_resp.text
    return listing


async def _completed_booking(
    client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
) -> dict:
    """Yakunlangan bron yaratadi (listing bilan birga) — sharh yozish uchun tayyor holat."""
    listing = await _create_listing(client, b2b_headers, admin_headers)

    topup_resp = await client.post(
        "/api/v1/wallet/topup", json={"amount": 1_000_000}, headers=b2c_headers
    )
    assert topup_resp.status_code == 200, topup_resp.text

    check_in = _next_monday()
    check_out = check_in + timedelta(days=2)
    booking_resp = await client.post(
        "/api/v1/bookings",
        json={
            "listing_id": listing["id"],
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests": 2,
            "guest_name": "Ali Valiyev",
            "guest_phone": "998911111111",
        },
        headers=b2c_headers,
    )
    assert booking_resp.status_code == 201, booking_resp.text
    booking = booking_resp.json()

    confirm_resp = await client.post(
        f"/api/v1/bookings/{booking['id']}/confirm", headers=b2b_headers
    )
    assert confirm_resp.status_code == 200, confirm_resp.text

    complete_resp = await client.post(
        f"/api/v1/bookings/{booking['id']}/complete", headers=b2b_headers
    )
    assert complete_resp.status_code == 200, complete_resp.text

    return {"listing": listing, "booking": complete_resp.json()}


async def _create_operator_and_tour(
    client: AsyncClient, b2b_headers: dict, admin_headers: dict
) -> dict:
    op_resp = await client.post("/api/v1/operators", json=OPERATOR_PAYLOAD, headers=b2b_headers)
    assert op_resp.status_code == 201, op_resp.text
    operator = op_resp.json()

    tour_resp = await client.post(
        "/api/v1/tours",
        json={**TOUR_PAYLOAD, "operator_id": operator["id"]},
        headers=b2b_headers,
    )
    assert tour_resp.status_code == 201, tour_resp.text
    tour = tour_resp.json()

    approve_resp = await client.post(
        f"/api/v1/admin/tours/{tour['id']}/approve", headers=admin_headers
    )
    assert approve_resp.status_code == 200, approve_resp.text
    return approve_resp.json()


class TestListingReviews:
    async def test_create_with_completed_booking_succeeds_and_updates_rating(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        ctx = await _completed_booking(client, b2b_headers, admin_headers, b2c_headers)

        resp = await client.post(
            "/api/v1/reviews",
            json={
                "listing_id": ctx["listing"]["id"],
                "booking_id": ctx["booking"]["id"],
                "stars": 5,
                "text": "Ajoyib joy, juda yoqdi, albatta qaytamiz!",
            },
            headers=b2c_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["verified"] is True

        listing_resp = await client.get(f"/api/v1/listings/{ctx['listing']['id']}")
        body = listing_resp.json()
        assert body["rating"] == 5.0
        assert body["rating_count"] == 1

    async def test_create_without_booking_id_returns_422(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers, admin_headers)
        resp = await client.post(
            "/api/v1/reviews",
            json={"listing_id": listing["id"], "stars": 5, "text": "Ajoyib joy edi haqiqatan!"},
            headers=b2c_headers,
        )
        assert resp.status_code == 422

    async def test_create_with_foreign_booking_returns_403(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        ctx = await _completed_booking(client, b2b_headers, admin_headers, b2c_headers)
        stranger_headers = await _register(client, "998977700001")

        resp = await client.post(
            "/api/v1/reviews",
            json={
                "listing_id": ctx["listing"]["id"],
                "booking_id": ctx["booking"]["id"],
                "stars": 5,
                "text": "Men bu yerda bo'lmaganman lekin sharh yozaman",
            },
            headers=stranger_headers,
        )
        assert resp.status_code == 403

    async def test_create_with_mismatched_listing_returns_400(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        ctx = await _completed_booking(client, b2b_headers, admin_headers, b2c_headers)
        other_listing = await _create_listing(client, b2b_headers, admin_headers)

        resp = await client.post(
            "/api/v1/reviews",
            json={
                "listing_id": other_listing["id"],
                "booking_id": ctx["booking"]["id"],
                "stars": 4,
                "text": "Bu boshqa listing uchun sharh, mos kelmasligi kerak",
            },
            headers=b2c_headers,
        )
        assert resp.status_code == 400

    async def test_create_with_non_completed_booking_returns_409(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers, admin_headers)
        await client.post(
            "/api/v1/wallet/topup", json={"amount": 1_000_000}, headers=b2c_headers
        )
        check_in = _next_monday()
        check_out = check_in + timedelta(days=2)
        booking_resp = await client.post(
            "/api/v1/bookings",
            json={
                "listing_id": listing["id"],
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "guests": 2,
                "guest_name": "Ali Valiyev",
                "guest_phone": "998911111111",
            },
            headers=b2c_headers,
        )
        booking = booking_resp.json()

        resp = await client.post(
            "/api/v1/reviews",
            json={
                "listing_id": listing["id"],
                "booking_id": booking["id"],
                "stars": 5,
                "text": "Hali yakunlanmagan bron uchun sharh yozishga urinish",
            },
            headers=b2c_headers,
        )
        assert resp.status_code == 409

    async def test_double_review_same_booking_returns_409(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        ctx = await _completed_booking(client, b2b_headers, admin_headers, b2c_headers)
        payload = {
            "listing_id": ctx["listing"]["id"],
            "booking_id": ctx["booking"]["id"],
            "stars": 5,
            "text": "Birinchi sharh, hammasi ajoyib bo'ldi",
        }
        first = await client.post("/api/v1/reviews", json=payload, headers=b2c_headers)
        assert first.status_code == 201, first.text

        second = await client.post(
            "/api/v1/reviews",
            json={**payload, "text": "Ikkinchi marta sharh yozishga urinish shu bronga"},
            headers=b2c_headers,
        )
        assert second.status_code == 409

    async def test_invalid_sub_score_key_returns_422(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        ctx = await _completed_booking(client, b2b_headers, admin_headers, b2c_headers)
        resp = await client.post(
            "/api/v1/reviews",
            json={
                "listing_id": ctx["listing"]["id"],
                "booking_id": ctx["booking"]["id"],
                "stars": 5,
                "text": "Sub score kaliti noto'g'ri bo'lgan holat uchun test",
                "sub_scores": {"parking": 5},
            },
            headers=b2c_headers,
        )
        assert resp.status_code == 422


class TestTourReviews:
    async def test_create_without_booking_succeeds_not_verified(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        tour = await _create_operator_and_tour(client, b2b_headers, admin_headers)

        resp = await client.post(
            "/api/v1/reviews",
            json={
                "tour_id": tour["id"],
                "stars": 4,
                "text": "Ekskursiya juda qiziqarli va bilimli o'tdi, rahmat!",
            },
            headers=b2c_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["verified"] is False

        tour_resp = await client.get(f"/api/v1/tours/{tour['id']}")
        body = tour_resp.json()
        assert body["rating"] == 4.0
        assert body["rating_count"] == 1

    async def test_double_review_same_tour_returns_409(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        tour = await _create_operator_and_tour(client, b2b_headers, admin_headers)
        payload = {"tour_id": tour["id"], "stars": 4, "text": "Birinchi sharh shu tur uchun"}
        first = await client.post("/api/v1/reviews", json=payload, headers=b2c_headers)
        assert first.status_code == 201, first.text

        second = await client.post(
            "/api/v1/reviews",
            json={**payload, "text": "Ikkinchi marta sharh yozishga urinish shu turga"},
            headers=b2c_headers,
        )
        assert second.status_code == 409


class TestUpdateAndDelete:
    async def test_only_author_can_update(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        ctx = await _completed_booking(client, b2b_headers, admin_headers, b2c_headers)
        create_resp = await client.post(
            "/api/v1/reviews",
            json={
                "listing_id": ctx["listing"]["id"],
                "booking_id": ctx["booking"]["id"],
                "stars": 3,
                "text": "Boshlang'ich sharh matni shu yerda turadi",
            },
            headers=b2c_headers,
        )
        review_id = create_resp.json()["id"]

        admin_attempt = await client.patch(
            f"/api/v1/reviews/{review_id}", json={"stars": 1}, headers=admin_headers
        )
        assert admin_attempt.status_code == 403

        author_update = await client.patch(
            f"/api/v1/reviews/{review_id}", json={"stars": 5}, headers=b2c_headers
        )
        assert author_update.status_code == 200
        assert author_update.json()["stars"] == 5

        listing_resp = await client.get(f"/api/v1/listings/{ctx['listing']['id']}")
        assert listing_resp.json()["rating"] == 5.0

    async def test_delete_recomputes_rating_to_zero(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        ctx = await _completed_booking(client, b2b_headers, admin_headers, b2c_headers)
        create_resp = await client.post(
            "/api/v1/reviews",
            json={
                "listing_id": ctx["listing"]["id"],
                "booking_id": ctx["booking"]["id"],
                "stars": 4,
                "text": "O'chiriladigan sharh uchun matn shu yerda",
            },
            headers=b2c_headers,
        )
        review_id = create_resp.json()["id"]

        delete_resp = await client.delete(f"/api/v1/reviews/{review_id}", headers=b2c_headers)
        assert delete_resp.status_code == 204

        listing_resp = await client.get(f"/api/v1/listings/{ctx['listing']['id']}")
        body = listing_resp.json()
        assert body["rating"] == 0.0
        assert body["rating_count"] == 0

    async def test_admin_can_delete(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        ctx = await _completed_booking(client, b2b_headers, admin_headers, b2c_headers)
        create_resp = await client.post(
            "/api/v1/reviews",
            json={
                "listing_id": ctx["listing"]["id"],
                "booking_id": ctx["booking"]["id"],
                "stars": 2,
                "text": "ADMIN tomonidan o'chiriladigan sharh matni",
            },
            headers=b2c_headers,
        )
        review_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/reviews/{review_id}", headers=admin_headers)
        assert resp.status_code == 204


class TestListReviews:
    async def test_requires_exactly_one_target(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers, admin_headers)

        neither = await client.get("/api/v1/reviews")
        assert neither.status_code == 400

        both = await client.get(
            "/api/v1/reviews", params={"listing_id": listing["id"], "tour_id": listing["id"]}
        )
        assert both.status_code == 400

    async def test_filters_by_listing(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        ctx = await _completed_booking(client, b2b_headers, admin_headers, b2c_headers)
        await client.post(
            "/api/v1/reviews",
            json={
                "listing_id": ctx["listing"]["id"],
                "booking_id": ctx["booking"]["id"],
                "stars": 5,
                "text": "Ro'yxatlashda ko'rinishi kerak bo'lgan sharh matni",
            },
            headers=b2c_headers,
        )

        resp = await client.get("/api/v1/reviews", params={"listing_id": ctx["listing"]["id"]})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
