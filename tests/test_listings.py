import io

from httpx import AsyncClient

from app.core.storage import get_storage
from app.main import app

LISTING_PAYLOAD = {
    "name": "Test Dacha",
    "type": "Dacha",
    "region": "Tashkent",
    "weekday_price": 100,
    "weekend_price": 150,
    "capacity": 4,
    "amenities": ["wifi", "pool"],
    "description": "Test tavsif",
}


async def _create_listing(client: AsyncClient, b2b_headers: dict, **overrides) -> dict:
    payload = {**LISTING_PAYLOAD, **overrides}
    resp = await client.post("/api/v1/listings", json=payload, headers=b2b_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _approve(client: AsyncClient, listing_id: str, admin_headers: dict) -> dict:
    resp = await client.post(f"/api/v1/admin/listings/{listing_id}/approve", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestListingCreateAndVerification:
    async def test_register_login_create_starts_unverified(self, client: AsyncClient):
        register_payload = {
            "name": "Ali",
            "surname": "Valiyev",
            "phone": "998911111111",
            "password": "password123",
            "role": "B2B",
        }
        resp = await client.post("/api/v1/auth/register", json=register_payload)
        assert resp.status_code == 200, resp.text
        access_token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"identifier": "998911111111", "password": "password123"},
        )
        assert login_resp.status_code == 200, login_resp.text

        listing = await _create_listing(client, headers)
        assert listing["verified"] is False
        assert listing["paused"] is False

    async def test_unverified_listing_not_in_public_search(
        self, client: AsyncClient, b2b_headers: dict
    ):
        await _create_listing(client, b2b_headers, name="Unverified Dacha")

        resp = await client.get("/api/v1/listings", params={"region": "Tashkent"})
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()["items"]]
        assert "Unverified Dacha" not in names

    async def test_admin_approve_makes_it_visible(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers, name="Now Verified Dacha")
        await _approve(client, listing["id"], admin_headers)

        resp = await client.get("/api/v1/listings", params={"region": "Tashkent"})
        names = [item["name"] for item in resp.json()["items"]]
        assert "Now Verified Dacha" in names


class TestOwnership:
    async def test_non_owner_cannot_patch(
        self, client: AsyncClient, b2b_headers: dict, b2c_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers)

        resp = await client.patch(
            f"/api/v1/listings/{listing['id']}", json={"name": "Hacked"}, headers=b2c_headers
        )
        assert resp.status_code == 403

    async def test_owner_can_patch_and_delete(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers)

        patch_resp = await client.patch(
            f"/api/v1/listings/{listing['id']}",
            json={"name": "Updated Name"},
            headers=b2b_headers,
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["name"] == "Updated Name"

        delete_resp = await client.delete(f"/api/v1/listings/{listing['id']}", headers=b2b_headers)
        assert delete_resp.status_code == 204

        get_resp = await client.get(f"/api/v1/listings/{listing['id']}", headers=admin_headers)
        assert get_resp.status_code == 404


class TestSearch:
    async def test_filters_by_type_region_price_amenities(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        match = await _create_listing(
            client,
            b2b_headers,
            name="Match Listing",
            type="Dacha",
            region="Samarkand",
            weekday_price=200,
            amenities=["wifi", "sauna"],
        )
        await _approve(client, match["id"], admin_headers)

        other = await _create_listing(
            client,
            b2b_headers,
            name="Other Listing",
            type="Hotel",
            region="Bukhara",
            weekday_price=50,
            amenities=["parking"],
        )
        await _approve(client, other["id"], admin_headers)

        resp = await client.get(
            "/api/v1/listings",
            params={
                "type": "Dacha",
                "region": "Samarkand",
                "min_price": 100,
                "max_price": 300,
                "amenities": ["wifi", "sauna"],
            },
        )
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()["items"]]
        assert "Match Listing" in names
        assert "Other Listing" not in names


class TestPhotos:
    async def test_upload_and_delete_photo(
        self, client: AsyncClient, b2b_headers: dict, tmp_path
    ):
        from app.core.storage import LocalDiskStorage

        app.dependency_overrides[get_storage] = lambda: LocalDiskStorage(base_dir=str(tmp_path))
        try:
            listing = await _create_listing(client, b2b_headers)

            photo_bytes = io.BytesIO(b"\xff\xd8\xff\xe0fake-jpeg-bytes")
            files = [("files", ("photo.jpg", photo_bytes, "image/jpeg"))]
            resp = await client.post(
                f"/api/v1/listings/{listing['id']}/photos", files=files, headers=b2b_headers
            )
            assert resp.status_code == 200, resp.text
            photos = resp.json()["photos"]
            assert len(photos) == 1
            photo_id = photos[0]["id"]

            delete_resp = await client.delete(
                f"/api/v1/listings/{listing['id']}/photos/{photo_id}", headers=b2b_headers
            )
            assert delete_resp.status_code == 204
        finally:
            app.dependency_overrides.pop(get_storage, None)
