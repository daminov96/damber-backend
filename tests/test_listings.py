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

    async def test_filters_by_query_text_and_min_rating(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, db_session
    ):
        from sqlalchemy import select

        from app.modules.listings.models import Listing

        found = await _create_listing(client, b2b_headers, name="Unikal Bogcha")
        await _approve(client, found["id"], admin_headers)
        other = await _create_listing(client, b2b_headers, name="Boshqa Dacha")
        await _approve(client, other["id"], admin_headers)

        listing_row = (
            await db_session.execute(select(Listing).where(Listing.id == found["id"]))
        ).scalar_one()
        listing_row.rating = 4.9
        await db_session.commit()

        resp = await client.get("/api/v1/listings", params={"query": "Unikal"})
        names = [item["name"] for item in resp.json()["items"]]
        assert "Unikal Bogcha" in names
        assert "Boshqa Dacha" not in names

        resp2 = await client.get("/api/v1/listings", params={"min_rating": 4.5})
        names2 = [item["name"] for item in resp2.json()["items"]]
        assert "Unikal Bogcha" in names2
        assert "Boshqa Dacha" not in names2

    async def test_sort_by_discount(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        discounted = await _create_listing(
            client, b2b_headers, name="Chegirmali", weekday_price=100, old_price=200
        )
        await _approve(client, discounted["id"], admin_headers)
        regular = await _create_listing(client, b2b_headers, name="Oddiy", weekday_price=100)
        await _approve(client, regular["id"], admin_headers)

        resp = await client.get("/api/v1/listings", params={"sort": "discount"})
        names = [item["name"] for item in resp.json()["items"]]
        assert names.index("Chegirmali") < names.index("Oddiy")

    async def test_views_increments_on_each_fetch(self, client: AsyncClient, b2b_headers: dict):
        listing = await _create_listing(client, b2b_headers)
        assert listing["views"] == 0

        for expected in (1, 2, 3):
            resp = await client.get(f"/api/v1/listings/{listing['id']}", headers=b2b_headers)
            assert resp.json()["views"] == expected


class TestAquaTypeAndOldPrice:
    async def test_create_aqua_listing(self, client: AsyncClient, b2b_headers: dict):
        listing = await _create_listing(
            client, b2b_headers, name="City Aquapark", type="Aqua", old_price=200
        )
        assert listing["type"] == "Aqua"
        assert listing["old_price"] == 200

    async def test_old_price_optional_and_defaults_to_none(
        self, client: AsyncClient, b2b_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers)
        assert listing["old_price"] is None

    async def test_extra_accepts_arbitrary_keys(self, client: AsyncClient, b2b_headers: dict):
        extra = {
            "atmBanks": "Kapitalbank, SQB",
            "nearbyExchanges": [{"name": "Ipoteka Bank", "distance": "300 m", "hours": "24/7"}],
            "alcoholPolicy": "allowed",
        }
        listing = await _create_listing(client, b2b_headers, extra=extra)
        assert listing["extra"] == extra


class TestModeration:
    async def test_admin_reject_sets_reason_and_hides_from_search(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers, name="Rejectable Dacha")

        resp = await client.post(
            f"/api/v1/admin/listings/{listing['id']}/reject",
            json={"reason": "Rasmlar sifatsiz"},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["rejected"] is True
        assert body["reject_reason"] == "Rasmlar sifatsiz"

        search_resp = await client.get("/api/v1/listings", params={"region": "Tashkent"})
        names = [item["name"] for item in search_resp.json()["items"]]
        assert "Rejectable Dacha" not in names

    async def test_editing_rejected_listing_resubmits_for_review(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers)
        await client.post(
            f"/api/v1/admin/listings/{listing['id']}/reject",
            json={"reason": "Sabab"},
            headers=admin_headers,
        )

        resp = await client.patch(
            f"/api/v1/listings/{listing['id']}",
            json={"description": "Yangilangan tavsif"},
            headers=b2b_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["rejected"] is False
        assert body["reject_reason"] is None

    async def test_reject_requires_admin(
        self, client: AsyncClient, b2b_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers)

        resp = await client.post(
            f"/api/v1/admin/listings/{listing['id']}/reject",
            json={"reason": "Sabab"},
            headers=b2b_headers,
        )
        assert resp.status_code == 403

    async def test_cannot_reject_already_verified_listing(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers)
        await _approve(client, listing["id"], admin_headers)

        resp = await client.post(
            f"/api/v1/admin/listings/{listing['id']}/reject",
            json={"reason": "Kech qoldi"},
            headers=admin_headers,
        )
        assert resp.status_code == 409

    async def test_admin_can_pause_others_listing(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers)
        await _approve(client, listing["id"], admin_headers)

        resp = await client.post(
            f"/api/v1/listings/{listing['id']}/pause", headers=admin_headers
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["paused"] is True


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


class TestUploadFile:
    async def test_upload_video_returns_url_without_mutating_listing(
        self, client: AsyncClient, b2b_headers: dict, tmp_path
    ):
        from app.core.storage import LocalDiskStorage

        app.dependency_overrides[get_storage] = lambda: LocalDiskStorage(base_dir=str(tmp_path))
        try:
            listing = await _create_listing(client, b2b_headers)
            assert listing["video_url"] is None

            video_bytes = io.BytesIO(b"fake-mp4-bytes")
            resp = await client.post(
                f"/api/v1/listings/{listing['id']}/upload-file",
                data={"field": "video"},
                files={"file": ("clip.mp4", video_bytes, "video/mp4")},
                headers=b2b_headers,
            )
            assert resp.status_code == 200, resp.text
            url = resp.json()["url"]
            assert url

            # Yuklash Listing'ni o'zgartirmaydi — alohida PATCH kerak
            get_resp = await client.get(f"/api/v1/listings/{listing['id']}", headers=b2b_headers)
            assert get_resp.json()["video_url"] is None

            patch_resp = await client.patch(
                f"/api/v1/listings/{listing['id']}",
                json={"video_url": url},
                headers=b2b_headers,
            )
            assert patch_resp.json()["video_url"] == url
        finally:
            app.dependency_overrides.pop(get_storage, None)

    async def test_upload_rejects_wrong_content_type(
        self, client: AsyncClient, b2b_headers: dict, tmp_path
    ):
        from app.core.storage import LocalDiskStorage

        app.dependency_overrides[get_storage] = lambda: LocalDiskStorage(base_dir=str(tmp_path))
        try:
            listing = await _create_listing(client, b2b_headers)
            resp = await client.post(
                f"/api/v1/listings/{listing['id']}/upload-file",
                data={"field": "license"},
                files={"file": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")},
                headers=b2b_headers,
            )
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.pop(get_storage, None)

    async def test_upload_requires_owner(
        self, client: AsyncClient, b2b_headers: dict, b2c_headers: dict, tmp_path
    ):
        from app.core.storage import LocalDiskStorage

        app.dependency_overrides[get_storage] = lambda: LocalDiskStorage(base_dir=str(tmp_path))
        try:
            listing = await _create_listing(client, b2b_headers)
            resp = await client.post(
                f"/api/v1/listings/{listing['id']}/upload-file",
                data={"field": "menu"},
                files={"file": ("menu.pdf", io.BytesIO(b"%PDF-"), "application/pdf")},
                headers=b2c_headers,
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_storage, None)
