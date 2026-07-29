import datetime
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


async def _create_operator(client: AsyncClient, b2b_headers: dict, **overrides) -> dict:
    payload = {**OPERATOR_PAYLOAD, **overrides}
    resp = await client.post("/api/v1/operators", json=payload, headers=b2b_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestCreateAndVisibility:
    async def test_create_generates_license_issued_and_default_founded(
        self, client: AsyncClient, b2b_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)
        current_year = datetime.date.today().year
        assert operator["founded"] == current_year
        assert str(current_year) in operator["license_issued"]

    async def test_create_invalid_tin_returns_422(self, client: AsyncClient, b2b_headers: dict):
        resp = await client.post(
            "/api/v1/operators", json={**OPERATOR_PAYLOAD, "tin": "12345"}, headers=b2b_headers
        )
        assert resp.status_code == 422

    async def test_visible_immediately_no_moderation(
        self, client: AsyncClient, b2b_headers: dict
    ):
        await _create_operator(client, b2b_headers, name="Instantly Visible Operator")

        resp = await client.get("/api/v1/operators")
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()["items"]]
        assert "Instantly Visible Operator" in names


class TestSearch:
    async def test_filters_by_region_spec_tag_and_query(
        self, client: AsyncClient, b2b_headers: dict
    ):
        await _create_operator(
            client, b2b_headers, name="Silk Road Tours", region="Samarkand", spec_tag="Tarixiy"
        )
        await _create_operator(
            client, b2b_headers, name="Eco Adventures", region="Bukhara", spec_tag="Ekoturizm"
        )

        resp = await client.get(
            "/api/v1/operators",
            params={"region": "Samarkand", "spec_tag": "Tarixiy", "query": "Silk"},
        )
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()["items"]]
        assert "Silk Road Tours" in names
        assert "Eco Adventures" not in names

    async def test_sort_by_name(self, client: AsyncClient, b2b_headers: dict):
        await _create_operator(client, b2b_headers, name="Zebra Tours")
        await _create_operator(client, b2b_headers, name="Alpha Tours")

        resp = await client.get("/api/v1/operators", params={"sort": "name"})
        names = [item["name"] for item in resp.json()["items"]]
        assert names.index("Alpha Tours") < names.index("Zebra Tours")


class TestOwnership:
    async def test_non_owner_cannot_update_or_delete(
        self, client: AsyncClient, b2b_headers: dict, b2c_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)

        patch_resp = await client.patch(
            f"/api/v1/operators/{operator['id']}", json={"name": "Hacked"}, headers=b2c_headers
        )
        assert patch_resp.status_code == 403

        delete_resp = await client.delete(
            f"/api/v1/operators/{operator['id']}", headers=b2c_headers
        )
        assert delete_resp.status_code == 403

    async def test_owner_can_update_and_delete(self, client: AsyncClient, b2b_headers: dict):
        operator = await _create_operator(client, b2b_headers)

        patch_resp = await client.patch(
            f"/api/v1/operators/{operator['id']}", json={"name": "Updated"}, headers=b2b_headers
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["name"] == "Updated"

        delete_resp = await client.delete(
            f"/api/v1/operators/{operator['id']}", headers=b2b_headers
        )
        assert delete_resp.status_code == 204

        get_resp = await client.get(f"/api/v1/operators/{operator['id']}")
        assert get_resp.status_code == 404

    async def test_admin_can_update(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)

        resp = await client.patch(
            f"/api/v1/operators/{operator['id']}",
            json={"name": "Admin edited"},
            headers=admin_headers,
        )
        assert resp.status_code == 200


class TestDeleteWithTours:
    async def test_delete_operator_with_tours_raises_conflict(
        self, client: AsyncClient, b2b_headers: dict
    ):
        operator = await _create_operator(client, b2b_headers)
        tour_payload = {
            "operator_id": operator["id"],
            "name": "Test tur",
            "duration": "3 kun / 2 tun",
            "region": "Tashkent",
            "meeting_point": "Toshkent vokzali",
            "price": 500000,
            "description": "Test tur tavsifi",
        }
        tour_resp = await client.post("/api/v1/tours", json=tour_payload, headers=b2b_headers)
        assert tour_resp.status_code == 201, tour_resp.text

        delete_resp = await client.delete(
            f"/api/v1/operators/{operator['id']}", headers=b2b_headers
        )
        assert delete_resp.status_code == 409


class TestMultipleProfiles:
    async def test_one_user_can_create_multiple_operators(
        self, client: AsyncClient, b2b_headers: dict
    ):
        await _create_operator(client, b2b_headers, name="Operator One")
        await _create_operator(client, b2b_headers, name="Operator Two")

        resp = await client.get("/api/v1/operators/mine", headers=b2b_headers)
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()]
        assert "Operator One" in names
        assert "Operator Two" in names


class TestPhotos:
    async def test_upload_and_delete_photo(
        self, client: AsyncClient, b2b_headers: dict, tmp_path
    ):
        from app.core.storage import LocalDiskStorage

        app.dependency_overrides[get_storage] = lambda: LocalDiskStorage(base_dir=str(tmp_path))
        try:
            operator = await _create_operator(client, b2b_headers)

            photo_bytes = io.BytesIO(b"\xff\xd8\xff\xe0fake-jpeg-bytes")
            files = [("files", ("photo.jpg", photo_bytes, "image/jpeg"))]
            resp = await client.post(
                f"/api/v1/operators/{operator['id']}/photos", files=files, headers=b2b_headers
            )
            assert resp.status_code == 200, resp.text
            photos = resp.json()["photos"]
            assert len(photos) == 1
            photo_id = photos[0]["id"]

            delete_resp = await client.delete(
                f"/api/v1/operators/{operator['id']}/photos/{photo_id}", headers=b2b_headers
            )
            assert delete_resp.status_code == 204
        finally:
            app.dependency_overrides.pop(get_storage, None)
