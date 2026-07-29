import io

from httpx import AsyncClient

from app.core.storage import get_storage
from app.main import app

GUIDE_PAYLOAD = {
    "name": "Aziz Karimov",
    "languages": ["O'zbek", "Rus", "Ingliz"],
    "region": "Tashkent",
    "service_areas": ["Toshkent", "Samarqand"],
    "specialties": ["Tarixiy turlar"],
    "hourly_price": 100000,
    "phone": "998911111111",
    "email": "guide@test.local",
    "description": "Tajribali gid, 10 yildan ortiq tajriba, tarixiy joylar bo'yicha mutaxassis.",
}


async def _create_guide(client: AsyncClient, b2b_headers: dict, **overrides) -> dict:
    payload = {**GUIDE_PAYLOAD, **overrides}
    resp = await client.post("/api/v1/guides", json=payload, headers=b2b_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestCreateAndVisibility:
    async def test_create_without_license_doc_is_not_certified(
        self, client: AsyncClient, b2b_headers: dict
    ):
        guide = await _create_guide(client, b2b_headers)
        assert guide["certified"] is False

    async def test_create_with_license_doc_is_certified(
        self, client: AsyncClient, b2b_headers: dict
    ):
        guide = await _create_guide(client, b2b_headers, license_doc_name="sertifikat.pdf")
        assert guide["certified"] is True

    async def test_client_sent_certified_is_ignored(self, client: AsyncClient, b2b_headers: dict):
        resp = await client.post(
            "/api/v1/guides", json={**GUIDE_PAYLOAD, "certified": True}, headers=b2b_headers
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["certified"] is False

    async def test_visible_immediately_no_moderation(
        self, client: AsyncClient, b2b_headers: dict
    ):
        await _create_guide(client, b2b_headers, name="Instantly Visible Guide")

        resp = await client.get("/api/v1/guides")
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()["items"]]
        assert "Instantly Visible Guide" in names


class TestValidation:
    async def test_single_word_name_returns_422(self, client: AsyncClient, b2b_headers: dict):
        resp = await client.post(
            "/api/v1/guides", json={**GUIDE_PAYLOAD, "name": "Aziz"}, headers=b2b_headers
        )
        assert resp.status_code == 422

    async def test_empty_languages_returns_422(self, client: AsyncClient, b2b_headers: dict):
        resp = await client.post(
            "/api/v1/guides", json={**GUIDE_PAYLOAD, "languages": []}, headers=b2b_headers
        )
        assert resp.status_code == 422

    async def test_empty_service_areas_returns_422(self, client: AsyncClient, b2b_headers: dict):
        resp = await client.post(
            "/api/v1/guides", json={**GUIDE_PAYLOAD, "service_areas": []}, headers=b2b_headers
        )
        assert resp.status_code == 422

    async def test_empty_specialties_returns_422(self, client: AsyncClient, b2b_headers: dict):
        resp = await client.post(
            "/api/v1/guides", json={**GUIDE_PAYLOAD, "specialties": []}, headers=b2b_headers
        )
        assert resp.status_code == 422

    async def test_no_pricing_returns_422(self, client: AsyncClient, b2b_headers: dict):
        payload = {**GUIDE_PAYLOAD}
        payload.pop("hourly_price")
        resp = await client.post("/api/v1/guides", json=payload, headers=b2b_headers)
        assert resp.status_code == 422

    async def test_has_car_without_model_returns_422(
        self, client: AsyncClient, b2b_headers: dict
    ):
        resp = await client.post(
            "/api/v1/guides", json={**GUIDE_PAYLOAD, "has_car": True}, headers=b2b_headers
        )
        assert resp.status_code == 422

    async def test_has_car_with_model_succeeds(self, client: AsyncClient, b2b_headers: dict):
        guide = await _create_guide(client, b2b_headers, has_car=True, car_model="Chevrolet Cobalt")
        assert guide["has_car"] is True
        assert guide["car_model"] == "Chevrolet Cobalt"


class TestSearch:
    async def test_filters_by_region_and_guide_type(
        self, client: AsyncClient, b2b_headers: dict
    ):
        await _create_guide(
            client,
            b2b_headers,
            name="Samarkand Guide",
            region="Samarkand",
            guide_type="Individual gid",
        )
        await _create_guide(
            client, b2b_headers, name="Bukhara Guide", region="Bukhara", guide_type="Gid-haydovchi"
        )

        resp = await client.get(
            "/api/v1/guides", params={"region": "Samarkand", "guide_type": "Individual gid"}
        )
        names = [item["name"] for item in resp.json()["items"]]
        assert "Samarkand Guide" in names
        assert "Bukhara Guide" not in names

    async def test_sort_by_name(self, client: AsyncClient, b2b_headers: dict):
        await _create_guide(client, b2b_headers, name="Zebra Guide")
        await _create_guide(client, b2b_headers, name="Alpha Guide")

        resp = await client.get("/api/v1/guides", params={"sort": "name"})
        names = [item["name"] for item in resp.json()["items"]]
        assert names.index("Alpha Guide") < names.index("Zebra Guide")


class TestOwnership:
    async def test_non_owner_cannot_update_or_delete(
        self, client: AsyncClient, b2b_headers: dict, b2c_headers: dict
    ):
        guide = await _create_guide(client, b2b_headers)

        patch_resp = await client.patch(
            f"/api/v1/guides/{guide['id']}", json={"name": "Hacked Person"}, headers=b2c_headers
        )
        assert patch_resp.status_code == 403

        delete_resp = await client.delete(f"/api/v1/guides/{guide['id']}", headers=b2c_headers)
        assert delete_resp.status_code == 403

    async def test_owner_can_update_and_delete(self, client: AsyncClient, b2b_headers: dict):
        guide = await _create_guide(client, b2b_headers)

        patch_resp = await client.patch(
            f"/api/v1/guides/{guide['id']}", json={"name": "Updated Name"}, headers=b2b_headers
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["name"] == "Updated Name"

        delete_resp = await client.delete(f"/api/v1/guides/{guide['id']}", headers=b2b_headers)
        assert delete_resp.status_code == 204

    async def test_update_recomputes_certified(self, client: AsyncClient, b2b_headers: dict):
        guide = await _create_guide(client, b2b_headers)
        assert guide["certified"] is False

        resp = await client.patch(
            f"/api/v1/guides/{guide['id']}",
            json={"license_doc_name": "sertifikat.pdf"},
            headers=b2b_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["certified"] is True


class TestDeleteWithTours:
    async def test_delete_guide_with_tours_raises_conflict(
        self, client: AsyncClient, b2b_headers: dict
    ):
        guide = await _create_guide(client, b2b_headers)
        tour_payload = {
            "guide_id": guide["id"],
            "name": "Test ekskursiya",
            "duration": "1 kun",
            "region": "Tashkent",
            "meeting_point": "Toshkent vokzali",
            "price": 200000,
            "description": "Test ekskursiya tavsifi",
        }
        tour_resp = await client.post("/api/v1/tours", json=tour_payload, headers=b2b_headers)
        assert tour_resp.status_code == 201, tour_resp.text

        delete_resp = await client.delete(f"/api/v1/guides/{guide['id']}", headers=b2b_headers)
        assert delete_resp.status_code == 409


class TestPhotos:
    async def test_upload_and_delete_photo(
        self, client: AsyncClient, b2b_headers: dict, tmp_path
    ):
        from app.core.storage import LocalDiskStorage

        app.dependency_overrides[get_storage] = lambda: LocalDiskStorage(base_dir=str(tmp_path))
        try:
            guide = await _create_guide(client, b2b_headers)

            photo_bytes = io.BytesIO(b"\xff\xd8\xff\xe0fake-jpeg-bytes")
            files = [("files", ("photo.jpg", photo_bytes, "image/jpeg"))]
            resp = await client.post(
                f"/api/v1/guides/{guide['id']}/photos", files=files, headers=b2b_headers
            )
            assert resp.status_code == 200, resp.text
            photos = resp.json()["photos"]
            assert len(photos) == 1
            photo_id = photos[0]["id"]

            delete_resp = await client.delete(
                f"/api/v1/guides/{guide['id']}/photos/{photo_id}", headers=b2b_headers
            )
            assert delete_resp.status_code == 204
        finally:
            app.dependency_overrides.pop(get_storage, None)
