import io

from httpx import AsyncClient

from app.core.storage import get_storage
from app.main import app

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
    "nights": 2,
    "region": "Samarkand",
    "meeting_point": "Toshkent temir yo'l vokzali",
    "price": 500000,
    "description": "Test tur tavsifi",
}

GUIDE_PAYLOAD = {
    "name": "Aziz Karimov",
    "languages": ["O'zbek", "Rus"],
    "region": "Tashkent",
    "service_areas": ["Toshkent"],
    "specialties": ["Tarixiy turlar"],
    "hourly_price": 100000,
    "phone": "998911111111",
    "email": "guide@test.local",
    "description": "Tajribali gid, tarixiy joylar bo'yicha mutaxassis, 10 yildan ortiq tajriba.",
}


async def _register(client: AsyncClient, phone: str, role: str = "B2B") -> dict:
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


async def _create_operator(client: AsyncClient, b2b_headers: dict, **overrides) -> dict:
    payload = {**OPERATOR_PAYLOAD, **overrides}
    resp = await client.post("/api/v1/operators", json=payload, headers=b2b_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_tour(
    client: AsyncClient, b2b_headers: dict, operator_id: str, **overrides
) -> dict:
    payload = {**TOUR_PAYLOAD, "operator_id": operator_id, **overrides}
    resp = await client.post("/api/v1/tours", json=payload, headers=b2b_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _approve_tour(client: AsyncClient, tour_id: str, admin_headers: dict) -> dict:
    resp = await client.post(f"/api/v1/admin/tours/{tour_id}/approve", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _create_guide(client: AsyncClient, b2b_headers: dict, **overrides) -> dict:
    payload = {**GUIDE_PAYLOAD, **overrides}
    resp = await client.post("/api/v1/guides", json=payload, headers=b2b_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestCreateAndOwnership:
    async def test_create_success_is_pending(self, client: AsyncClient, b2b_headers: dict):
        operator = await _create_operator(client, b2b_headers)
        tour = await _create_tour(client, b2b_headers, operator["id"])
        assert tour["pending"] is True

    async def test_create_with_foreign_operator_returns_403(
        self, client: AsyncClient, b2b_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)
        other_headers = await _register(client, "998977200001", role="B2B")

        resp = await client.post(
            "/api/v1/tours",
            json={**TOUR_PAYLOAD, "operator_id": operator["id"]},
            headers=other_headers,
        )
        assert resp.status_code == 403


class TestVisibility:
    async def test_pending_tour_hidden_from_public_search(
        self, client: AsyncClient, b2b_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)
        await _create_tour(client, b2b_headers, operator["id"], name="Hidden Tour")

        resp = await client.get("/api/v1/tours")
        names = [item["name"] for item in resp.json()["items"]]
        assert "Hidden Tour" not in names

    async def test_pending_tour_404_for_stranger(
        self, client: AsyncClient, b2b_headers: dict, b2c_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)
        tour = await _create_tour(client, b2b_headers, operator["id"])

        resp = await client.get(f"/api/v1/tours/{tour['id']}", headers=b2c_headers)
        assert resp.status_code == 404

    async def test_owner_and_admin_can_see_pending(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)
        tour = await _create_tour(client, b2b_headers, operator["id"])

        owner_resp = await client.get(f"/api/v1/tours/{tour['id']}", headers=b2b_headers)
        assert owner_resp.status_code == 200
        admin_resp = await client.get(f"/api/v1/tours/{tour['id']}", headers=admin_headers)
        assert admin_resp.status_code == 200

    async def test_approve_makes_visible(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)
        tour = await _create_tour(client, b2b_headers, operator["id"], name="Now Visible Tour")
        await _approve_tour(client, tour["id"], admin_headers)

        resp = await client.get("/api/v1/tours")
        names = [item["name"] for item in resp.json()["items"]]
        assert "Now Visible Tour" in names


class TestSearch:
    async def test_filters_by_region_and_nights_range(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)
        match = await _create_tour(
            client, b2b_headers, operator["id"], name="Match Tour", region="Samarkand", nights=2
        )
        await _approve_tour(client, match["id"], admin_headers)
        other = await _create_tour(
            client, b2b_headers, operator["id"], name="Other Tour", region="Bukhara", nights=10
        )
        await _approve_tour(client, other["id"], admin_headers)

        resp = await client.get(
            "/api/v1/tours", params={"region": "Samarkand", "nights_min": 1, "nights_max": 3}
        )
        names = [item["name"] for item in resp.json()["items"]]
        assert "Match Tour" in names
        assert "Other Tour" not in names

    async def test_sort_by_price(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)
        cheap = await _create_tour(
            client, b2b_headers, operator["id"], name="Cheap Tour", price=100000
        )
        await _approve_tour(client, cheap["id"], admin_headers)
        expensive = await _create_tour(
            client, b2b_headers, operator["id"], name="Expensive Tour", price=900000
        )
        await _approve_tour(client, expensive["id"], admin_headers)

        resp = await client.get("/api/v1/tours", params={"sort": "price_asc"})
        names = [item["name"] for item in resp.json()["items"]]
        assert names.index("Cheap Tour") < names.index("Expensive Tour")


class TestEditAndDelete:
    async def test_non_owner_cannot_update_or_delete(
        self, client: AsyncClient, b2b_headers: dict, b2c_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)
        tour = await _create_tour(client, b2b_headers, operator["id"])

        patch_resp = await client.patch(
            f"/api/v1/tours/{tour['id']}", json={"name": "Hacked"}, headers=b2c_headers
        )
        assert patch_resp.status_code == 403

        delete_resp = await client.delete(f"/api/v1/tours/{tour['id']}", headers=b2c_headers)
        assert delete_resp.status_code == 403

    async def test_owner_can_update_and_delete(self, client: AsyncClient, b2b_headers: dict):
        operator = await _create_operator(client, b2b_headers)
        tour = await _create_tour(client, b2b_headers, operator["id"])

        patch_resp = await client.patch(
            f"/api/v1/tours/{tour['id']}", json={"name": "Updated"}, headers=b2b_headers
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["name"] == "Updated"

        delete_resp = await client.delete(f"/api/v1/tours/{tour['id']}", headers=b2b_headers)
        assert delete_resp.status_code == 204


class TestPhotos:
    async def test_upload_and_delete_photo(
        self, client: AsyncClient, b2b_headers: dict, tmp_path
    ):
        from app.core.storage import LocalDiskStorage

        app.dependency_overrides[get_storage] = lambda: LocalDiskStorage(base_dir=str(tmp_path))
        try:
            operator = await _create_operator(client, b2b_headers)
            tour = await _create_tour(client, b2b_headers, operator["id"])

            photo_bytes = io.BytesIO(b"\xff\xd8\xff\xe0fake-jpeg-bytes")
            files = [("files", ("photo.jpg", photo_bytes, "image/jpeg"))]
            resp = await client.post(
                f"/api/v1/tours/{tour['id']}/photos", files=files, headers=b2b_headers
            )
            assert resp.status_code == 200, resp.text
            photos = resp.json()["photos"]
            assert len(photos) == 1
            photo_id = photos[0]["id"]

            delete_resp = await client.delete(
                f"/api/v1/tours/{tour['id']}/photos/{photo_id}", headers=b2b_headers
            )
            assert delete_resp.status_code == 204
        finally:
            app.dependency_overrides.pop(get_storage, None)


class TestBookingInquiry:
    async def test_create_booking_computes_total_estimate(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)
        tour = await _create_tour(client, b2b_headers, operator["id"], price=200000)
        await _approve_tour(client, tour["id"], admin_headers)

        resp = await client.post(
            f"/api/v1/tours/{tour['id']}/bookings",
            json={"name": "Mijoz", "phone": "998911112233", "people": 3},
            headers=b2c_headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["total_estimate"] == 600000
        assert body["status"] == "pending"

    async def test_owner_confirms_then_second_confirm_conflicts(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)
        tour = await _create_tour(client, b2b_headers, operator["id"])
        await _approve_tour(client, tour["id"], admin_headers)

        create_resp = await client.post(
            f"/api/v1/tours/{tour['id']}/bookings",
            json={"name": "Mijoz", "phone": "998911112233", "people": 2},
            headers=b2c_headers,
        )
        booking_id = create_resp.json()["id"]

        confirm_resp = await client.post(
            f"/api/v1/tour-bookings/{booking_id}/confirm", headers=b2b_headers
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["status"] == "confirmed"

        second_confirm = await client.post(
            f"/api/v1/tour-bookings/{booking_id}/confirm", headers=b2b_headers
        )
        assert second_confirm.status_code == 409

    async def test_non_owner_cannot_confirm(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)
        tour = await _create_tour(client, b2b_headers, operator["id"])
        await _approve_tour(client, tour["id"], admin_headers)

        create_resp = await client.post(
            f"/api/v1/tours/{tour['id']}/bookings",
            json={"name": "Mijoz", "phone": "998911112233", "people": 1},
            headers=b2c_headers,
        )
        booking_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/tour-bookings/{booking_id}/confirm", headers=b2c_headers
        )
        assert resp.status_code == 403

    async def test_client_sees_own_bookings(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)
        tour = await _create_tour(client, b2b_headers, operator["id"])
        await _approve_tour(client, tour["id"], admin_headers)
        await client.post(
            f"/api/v1/tours/{tour['id']}/bookings",
            json={"name": "Mijoz", "phone": "998911112233", "people": 1},
            headers=b2c_headers,
        )

        resp = await client.get("/api/v1/tour-bookings/mine", headers=b2c_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    async def test_host_lists_bookings_for_their_tour(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)
        tour = await _create_tour(client, b2b_headers, operator["id"])
        await _approve_tour(client, tour["id"], admin_headers)
        await client.post(
            f"/api/v1/tours/{tour['id']}/bookings",
            json={"name": "Mijoz", "phone": "998911112233", "people": 1},
            headers=b2c_headers,
        )

        resp = await client.get(f"/api/v1/tours/{tour['id']}/bookings", headers=b2b_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


class TestGuideOwnership:
    async def test_create_with_guide_id_succeeds_and_copies_owner(
        self, client: AsyncClient, b2b_headers: dict
    ):
        guide = await _create_guide(client, b2b_headers)
        resp = await client.post(
            "/api/v1/tours",
            json={**TOUR_PAYLOAD, "guide_id": guide["id"]},
            headers=b2b_headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["guide_id"] == guide["id"]
        assert body["operator_id"] is None
        assert body["owner_id"] == guide["owner_id"]

    async def test_both_operator_and_guide_id_returns_422(
        self, client: AsyncClient, b2b_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)
        guide = await _create_guide(client, b2b_headers)

        resp = await client.post(
            "/api/v1/tours",
            json={**TOUR_PAYLOAD, "operator_id": operator["id"], "guide_id": guide["id"]},
            headers=b2b_headers,
        )
        assert resp.status_code == 422

    async def test_neither_operator_nor_guide_id_returns_422(
        self, client: AsyncClient, b2b_headers: dict
    ):
        resp = await client.post("/api/v1/tours", json=TOUR_PAYLOAD, headers=b2b_headers)
        assert resp.status_code == 422

    async def test_foreign_guide_returns_403(self, client: AsyncClient, b2b_headers: dict):
        guide = await _create_guide(client, b2b_headers)
        other_headers = await _register(client, "998977200002", role="B2B")

        resp = await client.post(
            "/api/v1/tours",
            json={**TOUR_PAYLOAD, "guide_id": guide["id"]},
            headers=other_headers,
        )
        assert resp.status_code == 403
