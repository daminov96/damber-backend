import io

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import get_storage
from app.main import app
from app.modules.listings.models import Listing

COMPANY_PAYLOAD = {
    "name": "Test Rent Company",
    "tin": "123456789",
    "license": "RENT-LIC-001",
    "license_doc_name": "guvohnoma.pdf",
    "phone": "998911111111",
    "email": "rentco@test.local",
    "office": "Toshkent, Chilonzor",
    "region": "Tashkent",
    "description": "Test tavsif",
    "pickup_zones": ["Toshkent aeroporti"],
    "payment_methods": ["Naqd", "Karta"],
}

LISTING_PAYLOAD = {
    "name": "Test RentCar",
    "type": "RentCar",
    "region": "Tashkent",
    "weekday_price": 300000,
    "weekend_price": 350000,
    "capacity": 4,
    "amenities": [],
    "description": "Test tavsif",
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


async def _create_company(client: AsyncClient, b2b_headers: dict, **overrides) -> dict:
    payload = {**COMPANY_PAYLOAD, **overrides}
    resp = await client.post("/api/v1/rent-companies", json=payload, headers=b2b_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_listing(client: AsyncClient, b2b_headers: dict, **overrides) -> dict:
    payload = {**LISTING_PAYLOAD, **overrides}
    resp = await client.post("/api/v1/listings", json=payload, headers=b2b_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _approve_listing(client: AsyncClient, listing_id: str, admin_headers: dict) -> dict:
    resp = await client.post(f"/api/v1/admin/listings/{listing_id}/approve", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestCreateAndVisibility:
    async def test_create_success_requires_pickup_zones_and_payment_methods(
        self, client: AsyncClient, b2b_headers: dict
    ):
        company = await _create_company(client, b2b_headers)
        assert company["pickup_zones"] == ["Toshkent aeroporti"]

    async def test_create_without_pickup_zones_returns_422(
        self, client: AsyncClient, b2b_headers: dict
    ):
        resp = await client.post(
            "/api/v1/rent-companies",
            json={**COMPANY_PAYLOAD, "pickup_zones": []},
            headers=b2b_headers,
        )
        assert resp.status_code == 422

    async def test_create_without_payment_methods_returns_422(
        self, client: AsyncClient, b2b_headers: dict
    ):
        resp = await client.post(
            "/api/v1/rent-companies",
            json={**COMPANY_PAYLOAD, "payment_methods": []},
            headers=b2b_headers,
        )
        assert resp.status_code == 422

    async def test_visible_immediately_no_moderation(
        self, client: AsyncClient, b2b_headers: dict
    ):
        await _create_company(client, b2b_headers, name="Instantly Visible Rent Co")

        resp = await client.get("/api/v1/rent-companies")
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()["items"]]
        assert "Instantly Visible Rent Co" in names


class TestSearch:
    async def test_filters_by_region_and_query(self, client: AsyncClient, b2b_headers: dict):
        await _create_company(client, b2b_headers, name="Samarkand Rent", region="Samarkand")
        await _create_company(client, b2b_headers, name="Bukhara Rent", region="Bukhara")

        resp = await client.get(
            "/api/v1/rent-companies", params={"region": "Samarkand", "query": "Samarkand"}
        )
        names = [item["name"] for item in resp.json()["items"]]
        assert "Samarkand Rent" in names
        assert "Bukhara Rent" not in names

    async def test_sort_by_name(self, client: AsyncClient, b2b_headers: dict):
        await _create_company(client, b2b_headers, name="Zebra Rent")
        await _create_company(client, b2b_headers, name="Alpha Rent")

        resp = await client.get("/api/v1/rent-companies", params={"sort": "name"})
        names = [item["name"] for item in resp.json()["items"]]
        assert names.index("Alpha Rent") < names.index("Zebra Rent")


class TestOwnership:
    async def test_non_owner_cannot_update_or_delete(
        self, client: AsyncClient, b2b_headers: dict, b2c_headers: dict
    ):
        company = await _create_company(client, b2b_headers)

        patch_resp = await client.patch(
            f"/api/v1/rent-companies/{company['id']}",
            json={"name": "Hacked"},
            headers=b2c_headers,
        )
        assert patch_resp.status_code == 403

        delete_resp = await client.delete(
            f"/api/v1/rent-companies/{company['id']}", headers=b2c_headers
        )
        assert delete_resp.status_code == 403

    async def test_owner_can_update_and_delete(self, client: AsyncClient, b2b_headers: dict):
        company = await _create_company(client, b2b_headers)

        patch_resp = await client.patch(
            f"/api/v1/rent-companies/{company['id']}",
            json={"name": "Updated"},
            headers=b2b_headers,
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["name"] == "Updated"

        delete_resp = await client.delete(
            f"/api/v1/rent-companies/{company['id']}", headers=b2b_headers
        )
        assert delete_resp.status_code == 204

    async def test_one_user_can_create_multiple_companies(
        self, client: AsyncClient, b2b_headers: dict
    ):
        await _create_company(client, b2b_headers, name="Company One")
        await _create_company(client, b2b_headers, name="Company Two")

        resp = await client.get("/api/v1/rent-companies/mine", headers=b2b_headers)
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()]
        assert "Company One" in names
        assert "Company Two" in names


class TestPhotos:
    async def test_upload_and_delete_photo(
        self, client: AsyncClient, b2b_headers: dict, tmp_path
    ):
        from app.core.storage import LocalDiskStorage

        app.dependency_overrides[get_storage] = lambda: LocalDiskStorage(base_dir=str(tmp_path))
        try:
            company = await _create_company(client, b2b_headers)

            photo_bytes = io.BytesIO(b"\xff\xd8\xff\xe0fake-jpeg-bytes")
            files = [("files", ("photo.jpg", photo_bytes, "image/jpeg"))]
            resp = await client.post(
                f"/api/v1/rent-companies/{company['id']}/photos", files=files, headers=b2b_headers
            )
            assert resp.status_code == 200, resp.text
            photos = resp.json()["photos"]
            assert len(photos) == 1
            photo_id = photos[0]["id"]

            delete_resp = await client.delete(
                f"/api/v1/rent-companies/{company['id']}/photos/{photo_id}", headers=b2b_headers
            )
            assert delete_resp.status_code == 204
        finally:
            app.dependency_overrides.pop(get_storage, None)


class TestListingLinkage:
    async def test_create_rent_car_listing_with_company_id_succeeds(
        self, client: AsyncClient, b2b_headers: dict
    ):
        company = await _create_company(client, b2b_headers)
        listing = await _create_listing(client, b2b_headers, company_id=company["id"])
        assert listing["company_id"] == company["id"]

    async def test_linking_to_foreign_company_returns_403(
        self, client: AsyncClient, b2b_headers: dict
    ):
        company = await _create_company(client, b2b_headers)
        other_headers = await _register(client, "998977400001", role="B2B")

        resp = await client.post(
            "/api/v1/listings",
            json={**LISTING_PAYLOAD, "company_id": company["id"]},
            headers=other_headers,
        )
        assert resp.status_code == 403

    async def test_company_id_on_non_rent_car_type_returns_400(
        self, client: AsyncClient, b2b_headers: dict
    ):
        company = await _create_company(client, b2b_headers)

        resp = await client.post(
            "/api/v1/listings",
            json={**LISTING_PAYLOAD, "type": "Dacha", "company_id": company["id"]},
            headers=b2b_headers,
        )
        assert resp.status_code == 400

    async def test_delete_company_sets_null_on_linked_listing(
        self, client: AsyncClient, db_session: AsyncSession, b2b_headers: dict
    ):
        company = await _create_company(client, b2b_headers)
        listing = await _create_listing(client, b2b_headers, company_id=company["id"])

        delete_resp = await client.delete(
            f"/api/v1/rent-companies/{company['id']}", headers=b2b_headers
        )
        assert delete_resp.status_code == 204

        db_listing = (
            await db_session.execute(select(Listing).where(Listing.id == listing["id"]))
        ).scalar_one()
        assert db_listing.company_id is None

    async def test_company_listings_endpoint_shows_only_approved(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        company = await _create_company(client, b2b_headers)
        listing = await _create_listing(
            client, b2b_headers, company_id=company["id"], name="Approved Car"
        )

        empty_resp = await client.get(f"/api/v1/rent-companies/{company['id']}/listings")
        assert empty_resp.json()["total"] == 0

        await _approve_listing(client, listing["id"], admin_headers)

        resp = await client.get(f"/api/v1/rent-companies/{company['id']}/listings")
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()["items"]]
        assert "Approved Car" in names
