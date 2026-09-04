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


async def _create_listing(client: AsyncClient, b2b_headers: dict, admin_headers: dict) -> dict:
    resp = await client.post("/api/v1/listings", json=LISTING_PAYLOAD, headers=b2b_headers)
    assert resp.status_code == 201, resp.text
    listing = resp.json()
    approve_resp = await client.post(
        f"/api/v1/admin/listings/{listing['id']}/approve", headers=admin_headers
    )
    assert approve_resp.status_code == 200, approve_resp.text
    return listing


async def test_add_favorite(
    client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
):
    listing = await _create_listing(client, b2b_headers, admin_headers)

    resp = await client.post(
        "/api/v1/favorites", json={"listing_id": listing["id"]}, headers=b2c_headers
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["listing_id"] == listing["id"]
    assert "id" in body
    assert "created_at" in body


async def test_add_favorite_twice_conflicts(
    client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
):
    listing = await _create_listing(client, b2b_headers, admin_headers)
    first = await client.post(
        "/api/v1/favorites", json={"listing_id": listing["id"]}, headers=b2c_headers
    )
    assert first.status_code == 201, first.text

    resp = await client.post(
        "/api/v1/favorites", json={"listing_id": listing["id"]}, headers=b2c_headers
    )

    assert resp.status_code == 409, resp.text


async def test_list_favorites(
    client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
):
    listing = await _create_listing(client, b2b_headers, admin_headers)
    add_resp = await client.post(
        "/api/v1/favorites", json={"listing_id": listing["id"]}, headers=b2c_headers
    )
    assert add_resp.status_code == 201, add_resp.text

    resp = await client.get("/api/v1/favorites", headers=b2c_headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["listing_id"] == listing["id"]


async def test_list_favorites_only_shows_own(
    client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
):
    listing = await _create_listing(client, b2b_headers, admin_headers)
    await client.post("/api/v1/favorites", json={"listing_id": listing["id"]}, headers=b2c_headers)

    resp = await client.get("/api/v1/favorites", headers=b2b_headers)

    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 0


async def test_remove_favorite(
    client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
):
    listing = await _create_listing(client, b2b_headers, admin_headers)
    await client.post("/api/v1/favorites", json={"listing_id": listing["id"]}, headers=b2c_headers)

    resp = await client.delete(f"/api/v1/favorites/{listing['id']}", headers=b2c_headers)

    assert resp.status_code == 204, resp.text
    list_resp = await client.get("/api/v1/favorites", headers=b2c_headers)
    assert list_resp.json()["total"] == 0


async def test_remove_favorite_not_found(
    client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
):
    listing = await _create_listing(client, b2b_headers, admin_headers)

    resp = await client.delete(f"/api/v1/favorites/{listing['id']}", headers=b2c_headers)

    assert resp.status_code == 404, resp.text


async def test_favorite_removed_when_listing_deleted(
    client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
):
    listing = await _create_listing(client, b2b_headers, admin_headers)
    await client.post("/api/v1/favorites", json={"listing_id": listing["id"]}, headers=b2c_headers)

    delete_resp = await client.delete(f"/api/v1/listings/{listing['id']}", headers=b2b_headers)
    assert delete_resp.status_code == 204, delete_resp.text

    list_resp = await client.get("/api/v1/favorites", headers=b2c_headers)
    assert list_resp.json()["total"] == 0
