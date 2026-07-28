from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.modules.bookings import pricing
from app.modules.bookings import service as bookings_service
from app.modules.bookings.models import BookingStatus, EscrowStatus
from app.modules.bookings.schemas import BookingCreateRequest
from app.modules.listings.models import Listing, ListingType, Region
from app.modules.users.models import User
from app.modules.wallet import service as wallet_service

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


def _next_monday() -> date:
    """Har doim kelajakdagi (yoki eng kamida bir haftadan keyingi) Dushanba —
    testlar haqiqiy ijro sanasidan qat'iy nazar barqaror bo'lishi uchun."""
    today = date.today()
    return today + timedelta(days=(7 - today.weekday()) % 7 or 7)


async def _create_listing(
    client: AsyncClient, b2b_headers: dict, admin_headers: dict, **overrides
) -> dict:
    payload = {**LISTING_PAYLOAD, **overrides}
    resp = await client.post("/api/v1/listings", json=payload, headers=b2b_headers)
    assert resp.status_code == 201, resp.text
    listing = resp.json()
    approve_resp = await client.post(
        f"/api/v1/admin/listings/{listing['id']}/approve", headers=admin_headers
    )
    assert approve_resp.status_code == 200, approve_resp.text
    return listing


async def _topup(client: AsyncClient, headers: dict, amount: float) -> None:
    resp = await client.post("/api/v1/wallet/topup", json={"amount": amount}, headers=headers)
    assert resp.status_code == 200, resp.text


def _default_booking_payload(listing_id: str, check_in: date, check_out: date, **overrides) -> dict:
    payload = {
        "listing_id": listing_id,
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "guests": 2,
        "guest_name": "Ali Valiyev",
        "guest_phone": "998911111111",
    }
    payload.update(overrides)
    return payload


async def _make_listing(db_session: AsyncSession, owner: User, **overrides) -> Listing:
    payload: dict = {
        "name": "Test Dacha",
        "type": ListingType.Dacha,
        "region": Region.Tashkent,
        "weekday_price": 100_000,
        "weekend_price": 150_000,
        "capacity": 4,
        "amenities": [],
        "description": "Test tavsif",
    }
    payload.update(overrides)
    listing = Listing(**payload, owner_id=owner.id, verified=True, paused=False)
    db_session.add(listing)
    await db_session.commit()
    await db_session.refresh(listing)
    return listing


async def _make_booking(db_session: AsyncSession, client: User, listing: Listing, **overrides):
    check_in = overrides.pop("check_in", _next_monday())
    check_out = overrides.pop("check_out", check_in + timedelta(days=2))
    payload = BookingCreateRequest(
        listing_id=listing.id,
        check_in=check_in,
        check_out=check_out,
        guests=overrides.pop("guests", 2),
        guest_name="Ali Valiyev",
        guest_phone="998911111111",
        **overrides,
    )
    return await bookings_service.create(db_session, client, payload)


# ── Pure pricing/refund funksiyalar (DB'siz) ──


class TestCountNights:
    def test_splits_weekday_and_weekend_nights(self):
        check_in = _next_monday()
        check_out = check_in + timedelta(days=7)
        result = pricing.count_nights(check_in, check_out, 100, 150, [], 0)
        assert result.weekdays == 4  # Dush-Pay
        assert result.weekends == 3  # Ju-Ya
        assert result.season_nights == 0
        assert result.season_extra == 0

    def test_season_surcharge_uses_zero_indexed_month(self):
        check_in = _next_monday()
        check_out = check_in + timedelta(days=2)
        result = pricing.count_nights(
            check_in, check_out, 100, 100, [check_in.month - 1], 20
        )
        assert result.season_nights == 2
        assert result.season_extra == 2 * round(100 * 20 / 100)

    def test_season_surcharge_not_applied_for_one_indexed_month_bug(self):
        check_in = _next_monday()
        check_out = check_in + timedelta(days=2)
        # 1-indekslangan oy (bug bo'lsa) noto'g'ri ishga tushadi — 0-indeks to'g'ri.
        result = pricing.count_nights(check_in, check_out, 100, 100, [check_in.month], 20)
        assert result.season_nights == 0
        assert result.season_extra == 0


class TestBestPromotion:
    def test_returns_none_without_promotions(self):
        assert pricing.best_promotion(None, 10, 3) is None

    def test_picks_highest_percent_when_multiple_qualify(self):
        promotions = {
            "earlyBird": {"days": 5, "percent": 10},
            "longStay": {"nights": 2, "percent": 25},
        }
        result = pricing.best_promotion(promotions, days_until=10, nights=5)
        assert result["percent"] == 25

    def test_last_minute_requires_non_negative_days_until(self):
        promotions = {"lastMinute": {"days": 3, "percent": 20}}
        assert pricing.best_promotion(promotions, days_until=-1, nights=1) is None
        assert pricing.best_promotion(promotions, days_until=2, nights=1)["percent"] == 20


class TestApplyPromo:
    def test_percent_code(self):
        result = pricing.apply_promo(100_000, "sayohat10")
        assert result.ok is True
        assert result.discount == 10_000
        assert result.final == 90_000

    def test_fixed_code(self):
        result = pricing.apply_promo(100_000, "YANGIUZ")
        assert result.discount == 50_000

    def test_unknown_code_no_discount(self):
        result = pricing.apply_promo(100_000, "NOPE")
        assert result.ok is False
        assert result.final == 100_000

    def test_no_code_no_discount(self):
        result = pricing.apply_promo(100_000, None)
        assert result.ok is False
        assert result.final == 100_000


class TestGuestRefund:
    NOW = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)

    @pytest.mark.parametrize(
        "policy,check_in,expected_percent",
        [
            ("Moslashuvchan", date(2026, 1, 11), 100),  # ~26 soat qoldi -> >=24
            ("Moslashuvchan", date(2026, 1, 10), 0),  # ~2 soat qoldi -> <24
            ("O'rtacha", date(2026, 1, 15), 100),  # ~5 kun -> >=3
            ("O'rtacha", date(2026, 1, 12), 50),  # ~2 kun -> [1,3)
            ("O'rtacha", date(2026, 1, 10), 0),  # <1 kun
            ("Qattiq", date(2026, 1, 20), 100),  # ~10 kun -> >=7
            ("Qattiq", date(2026, 1, 13), 0),  # ~3 kun -> <7
            ("Qaytarilmaydi", date(2026, 2, 10), 0),  # doim 0
        ],
    )
    def test_refund_tier(self, policy, check_in, expected_percent):
        result = pricing.guest_refund(policy, check_in, 10_000, self.NOW)
        assert result.percent == expected_percent
        assert result.amount == round(10_000 * expected_percent / 100)
        assert result.burnt == 10_000 - result.amount


class TestHostRejectRefund:
    def test_always_full_refund(self):
        result = pricing.host_reject_refund(5_000)
        assert result.percent == 100
        assert result.amount == 5_000
        assert result.burnt == 0


# ── Narx oldindan ko'rish (GET /bookings/quote) ──


class TestQuote:
    async def test_quote_breakdown(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers, admin_headers)
        check_in = _next_monday()
        check_out = check_in + timedelta(days=7)

        resp = await client.get(
            "/api/v1/bookings/quote",
            params={
                "listing_id": listing["id"],
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "guests": 2,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["weekdays"] == 4
        assert body["weekends"] == 3
        assert body["prepay_percent"] == 15
        assert body["total"] == 4 * 100_000 + 3 * 150_000
        assert body["advance"] == round(body["total"] * 0.15)

    async def test_quote_invalid_dates_returns_400(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers, admin_headers)
        check_in = _next_monday()

        resp = await client.get(
            "/api/v1/bookings/quote",
            params={
                "listing_id": listing["id"],
                "check_in": check_in.isoformat(),
                "check_out": check_in.isoformat(),
                "guests": 2,
            },
        )
        assert resp.status_code == 400

    async def test_quote_surfaces_min_stay_blocked_and_capacity_flags(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict
    ):
        check_in = _next_monday()
        check_out = check_in + timedelta(days=2)
        blocked = (check_in + timedelta(days=1)).isoformat()
        listing = await _create_listing(
            client,
            b2b_headers,
            admin_headers,
            capacity=2,
            extra={"minStay": 5, "blockedDates": [blocked]},
        )

        resp = await client.get(
            "/api/v1/bookings/quote",
            params={
                "listing_id": listing["id"],
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "guests": 5,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["min_stay"] == 5
        assert body["blocked_in_range"] == [blocked]
        assert body["over_capacity"] is True


# ── Bron yaratish ──


class TestCreateBooking:
    async def test_success_debits_wallet_and_sets_pending_held(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers, admin_headers)
        await _topup(client, b2c_headers, 1_000_000)
        check_in = _next_monday()
        check_out = check_in + timedelta(days=2)

        resp = await client.post(
            "/api/v1/bookings",
            json=_default_booking_payload(listing["id"], check_in, check_out),
            headers=b2c_headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "pending"
        assert body["escrow"] == "held"
        assert body["advance_amount"] > 0

        balance_resp = await client.get("/api/v1/wallet/balance", headers=b2c_headers)
        assert balance_resp.json()["balance"] == pytest.approx(1_000_000 - body["advance_amount"])

    async def test_insufficient_balance_returns_409_no_side_effects(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers, admin_headers)
        check_in = _next_monday()
        check_out = check_in + timedelta(days=2)

        resp = await client.post(
            "/api/v1/bookings",
            json=_default_booking_payload(listing["id"], check_in, check_out),
            headers=b2c_headers,
        )
        assert resp.status_code == 409

        balance_resp = await client.get("/api/v1/wallet/balance", headers=b2c_headers)
        assert balance_resp.json()["balance"] == 0
        mine_resp = await client.get("/api/v1/bookings/mine", headers=b2c_headers)
        assert mine_resp.json()["total"] == 0

    async def test_overlapping_dates_returns_409(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers, admin_headers)
        await _topup(client, b2c_headers, 10_000_000)
        check_in = _next_monday()
        check_out = check_in + timedelta(days=3)

        first = await client.post(
            "/api/v1/bookings",
            json=_default_booking_payload(listing["id"], check_in, check_out),
            headers=b2c_headers,
        )
        assert first.status_code == 201, first.text

        overlap_in = check_in + timedelta(days=1)
        overlap_out = check_out + timedelta(days=1)
        second = await client.post(
            "/api/v1/bookings",
            json=_default_booking_payload(listing["id"], overlap_in, overlap_out),
            headers=b2c_headers,
        )
        assert second.status_code == 409

    async def test_adjacent_non_overlapping_dates_succeeds(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers, admin_headers)
        await _topup(client, b2c_headers, 10_000_000)
        check_in = _next_monday()
        mid = check_in + timedelta(days=2)
        check_out = mid + timedelta(days=2)

        first = await client.post(
            "/api/v1/bookings",
            json=_default_booking_payload(listing["id"], check_in, mid),
            headers=b2c_headers,
        )
        assert first.status_code == 201, first.text

        second = await client.post(
            "/api/v1/bookings",
            json=_default_booking_payload(listing["id"], mid, check_out),
            headers=b2c_headers,
        )
        assert second.status_code == 201, second.text

    async def test_blocked_date_returns_400(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        check_in = _next_monday()
        check_out = check_in + timedelta(days=3)
        blocked_date = (check_in + timedelta(days=1)).isoformat()
        listing = await _create_listing(
            client, b2b_headers, admin_headers, extra={"blockedDates": [blocked_date]}
        )
        await _topup(client, b2c_headers, 10_000_000)

        resp = await client.post(
            "/api/v1/bookings",
            json=_default_booking_payload(listing["id"], check_in, check_out),
            headers=b2c_headers,
        )
        assert resp.status_code == 400

    async def test_below_min_stay_returns_400(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers, admin_headers, extra={"minStay": 3})
        await _topup(client, b2c_headers, 10_000_000)
        check_in = _next_monday()
        check_out = check_in + timedelta(days=1)

        resp = await client.post(
            "/api/v1/bookings",
            json=_default_booking_payload(listing["id"], check_in, check_out),
            headers=b2c_headers,
        )
        assert resp.status_code == 400

    async def test_over_capacity_returns_400(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        listing = await _create_listing(client, b2b_headers, admin_headers, capacity=2)
        await _topup(client, b2c_headers, 10_000_000)
        check_in = _next_monday()
        check_out = check_in + timedelta(days=1)

        resp = await client.post(
            "/api/v1/bookings",
            json=_default_booking_payload(listing["id"], check_in, check_out, guests=5),
            headers=b2c_headers,
        )
        assert resp.status_code == 400


# ── Holat siklasi (confirm/reject/complete) — servis darajasida, balans tekshiruvi uchun ──


class TestLifecycle:
    async def test_confirm_pending_to_confirmed(
        self, db_session: AsyncSession, b2b_user: User, b2c_user: User
    ):
        listing = await _make_listing(db_session, b2b_user)
        await wallet_service.topup(db_session, b2c_user, 1_000_000, None)
        booking = await _make_booking(db_session, b2c_user, listing)

        confirmed = await bookings_service.confirm(db_session, booking.id, b2b_user)
        assert confirmed.status == BookingStatus.confirmed
        assert confirmed.confirmed_at is not None

    async def test_confirm_non_pending_raises_conflict(
        self, db_session: AsyncSession, b2b_user: User, b2c_user: User
    ):
        listing = await _make_listing(db_session, b2b_user)
        await wallet_service.topup(db_session, b2c_user, 1_000_000, None)
        booking = await _make_booking(db_session, b2c_user, listing)
        await bookings_service.confirm(db_session, booking.id, b2b_user)

        with pytest.raises(ConflictError):
            await bookings_service.confirm(db_session, booking.id, b2b_user)

    async def test_reject_refunds_full_advance(
        self, db_session: AsyncSession, b2b_user: User, b2c_user: User
    ):
        listing = await _make_listing(db_session, b2b_user)
        await wallet_service.topup(db_session, b2c_user, 1_000_000, None)
        booking = await _make_booking(db_session, b2c_user, listing)
        balance_after_booking = b2c_user.wallet_balance

        rejected = await bookings_service.reject(db_session, booking.id, b2b_user, "Sabab")
        assert rejected.status == BookingStatus.rejected
        assert rejected.escrow == EscrowStatus.refunded
        assert b2c_user.wallet_balance == balance_after_booking + float(booking.advance_amount)

    async def test_reject_non_pending_raises_conflict(
        self, db_session: AsyncSession, b2b_user: User, b2c_user: User
    ):
        listing = await _make_listing(db_session, b2b_user)
        await wallet_service.topup(db_session, b2c_user, 1_000_000, None)
        booking = await _make_booking(db_session, b2c_user, listing)
        await bookings_service.confirm(db_session, booking.id, b2b_user)

        with pytest.raises(ConflictError):
            await bookings_service.reject(db_session, booking.id, b2b_user, None)

    async def test_complete_releases_escrow_to_owner(
        self, db_session: AsyncSession, b2b_user: User, b2c_user: User
    ):
        listing = await _make_listing(db_session, b2b_user)
        await wallet_service.topup(db_session, b2c_user, 1_000_000, None)
        booking = await _make_booking(db_session, b2c_user, listing)
        await bookings_service.confirm(db_session, booking.id, b2b_user)
        owner_balance_before = float(b2b_user.wallet_balance)

        completed = await bookings_service.complete(db_session, booking.id, b2b_user)
        assert completed.status == BookingStatus.completed
        assert completed.escrow == EscrowStatus.released
        assert b2b_user.wallet_balance == owner_balance_before + float(booking.advance_amount)

    async def test_complete_wrong_status_raises_conflict(
        self, db_session: AsyncSession, b2b_user: User, b2c_user: User
    ):
        listing = await _make_listing(db_session, b2b_user)
        await wallet_service.topup(db_session, b2c_user, 1_000_000, None)
        booking = await _make_booking(db_session, b2c_user, listing)  # hali pending

        with pytest.raises(ConflictError):
            await bookings_service.complete(db_session, booking.id, b2b_user)

    async def test_complete_succeeds_for_zero_advance_booking(
        self, db_session: AsyncSession, b2b_user: User, b2c_user: User
    ):
        """0% prepay bronda escrow=None qoladi — complete() shunga qaramay ishlashi kerak
        (frontend'dagi "faqat escrow=held" gap'i backend uchun tuzatildi)."""
        listing = await _make_listing(db_session, b2b_user, extra={"prepayPercent": 0})
        booking = await _make_booking(db_session, b2c_user, listing)
        assert booking.escrow is None
        await bookings_service.confirm(db_session, booking.id, b2b_user)

        completed = await bookings_service.complete(db_session, booking.id, b2b_user)
        assert completed.status == BookingStatus.completed


# ── Bekor qilish — siyosat-asosli qaytarish ──


class TestCancelRefundTiers:
    async def test_cancel_full_refund_when_flexible_and_far_from_checkin(
        self, db_session: AsyncSession, b2b_user: User, b2c_user: User
    ):
        listing = await _make_listing(
            db_session,
            b2b_user,
            extra={
                "rules": {"cancellation": "Moslashuvchan", "pets": "", "smoking": "", "events": ""}
            },
        )
        await wallet_service.topup(db_session, b2c_user, 1_000_000, None)
        booking = await _make_booking(
            db_session, b2c_user, listing, check_in=date(2026, 1, 11), check_out=date(2026, 1, 13)
        )
        client_balance_after_booking = b2c_user.wallet_balance
        advance = float(booking.advance_amount)
        now = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)

        cancelled = await bookings_service.cancel(db_session, booking.id, b2c_user, now=now)
        assert cancelled.status == BookingStatus.cancelled
        assert cancelled.escrow == EscrowStatus.refunded
        assert b2c_user.wallet_balance == client_balance_after_booking + advance

    async def test_cancel_partial_refund_moderate_burns_remainder_to_owner(
        self, db_session: AsyncSession, b2b_user: User, b2c_user: User
    ):
        listing = await _make_listing(
            db_session,
            b2b_user,
            extra={"rules": {"cancellation": "O'rtacha", "pets": "", "smoking": "", "events": ""}},
        )
        await wallet_service.topup(db_session, b2c_user, 1_000_000, None)
        booking = await _make_booking(
            db_session, b2c_user, listing, check_in=date(2026, 1, 12), check_out=date(2026, 1, 14)
        )
        client_balance_after_booking = b2c_user.wallet_balance
        owner_balance_before = float(b2b_user.wallet_balance)
        advance = float(booking.advance_amount)
        now = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)

        cancelled = await bookings_service.cancel(db_session, booking.id, b2c_user, now=now)
        expected_refund = round(advance * 50 / 100)
        assert cancelled.status == BookingStatus.cancelled
        assert b2c_user.wallet_balance == client_balance_after_booking + expected_refund
        assert b2b_user.wallet_balance == owner_balance_before + (advance - expected_refund)

    async def test_cancel_zero_advance_booking_no_wallet_side_effects(
        self, db_session: AsyncSession, b2b_user: User, b2c_user: User
    ):
        listing = await _make_listing(db_session, b2b_user, extra={"prepayPercent": 0})
        booking = await _make_booking(db_session, b2c_user, listing)
        assert booking.escrow is None
        client_balance_before = b2c_user.wallet_balance
        owner_balance_before = b2b_user.wallet_balance

        cancelled = await bookings_service.cancel(db_session, booking.id, b2c_user)
        assert cancelled.status == BookingStatus.cancelled
        assert cancelled.escrow is None
        assert b2c_user.wallet_balance == client_balance_before
        assert b2b_user.wallet_balance == owner_balance_before

    async def test_cancel_non_pending_or_confirmed_raises_conflict(
        self, db_session: AsyncSession, b2b_user: User, b2c_user: User
    ):
        listing = await _make_listing(db_session, b2b_user)
        await wallet_service.topup(db_session, b2c_user, 1_000_000, None)
        booking = await _make_booking(db_session, b2c_user, listing)
        await bookings_service.confirm(db_session, booking.id, b2b_user)
        await bookings_service.complete(db_session, booking.id, b2b_user)

        with pytest.raises(ConflictError):
            await bookings_service.cancel(db_session, booking.id, b2c_user)


# ── Rad etilgan bronni qayta tiklash ──


class TestRestore:
    async def test_restore_rejected_booking_reclaims_refund(
        self, db_session: AsyncSession, b2b_user: User, b2c_user: User
    ):
        listing = await _make_listing(db_session, b2b_user)
        await wallet_service.topup(db_session, b2c_user, 1_000_000, None)
        booking = await _make_booking(db_session, b2c_user, listing)
        balance_before_reject = b2c_user.wallet_balance
        await bookings_service.reject(db_session, booking.id, b2b_user, None)
        assert b2c_user.wallet_balance == balance_before_reject + float(booking.advance_amount)

        restored = await bookings_service.restore(db_session, booking.id, b2b_user)
        assert restored.status == BookingStatus.pending
        assert restored.escrow == EscrowStatus.held
        assert b2c_user.wallet_balance == balance_before_reject

    async def test_restore_insufficient_balance_raises_conflict(
        self, db_session: AsyncSession, b2b_user: User, b2c_user: User
    ):
        listing = await _make_listing(db_session, b2b_user)
        await wallet_service.topup(db_session, b2c_user, 1_000_000, None)
        booking = await _make_booking(db_session, b2c_user, listing)
        await bookings_service.reject(db_session, booking.id, b2b_user, None)
        # Mijoz qaytarilgan pulni boshqa joyga sarflaydi — restore uchun yetmaydi
        await wallet_service.pay(db_session, b2c_user, b2c_user.wallet_balance, "Boshqa xarajat")

        with pytest.raises(ConflictError):
            await bookings_service.restore(db_session, booking.id, b2b_user)

    async def test_restore_non_rejected_raises_conflict(
        self, db_session: AsyncSession, b2b_user: User, b2c_user: User
    ):
        listing = await _make_listing(db_session, b2b_user)
        await wallet_service.topup(db_session, b2c_user, 1_000_000, None)
        booking = await _make_booking(db_session, b2c_user, listing)

        with pytest.raises(ConflictError):
            await bookings_service.restore(db_session, booking.id, b2b_user)


# ── Ruxsat tekshiruvlari ──


class TestPermissions:
    async def _create_pending_booking(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ) -> str:
        listing = await _create_listing(client, b2b_headers, admin_headers)
        await _topup(client, b2c_headers, 1_000_000)
        check_in = _next_monday()
        check_out = check_in + timedelta(days=2)
        resp = await client.post(
            "/api/v1/bookings",
            json=_default_booking_payload(listing["id"], check_in, check_out),
            headers=b2c_headers,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()["id"]

    async def test_non_participant_cannot_view_booking(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        booking_id = await self._create_pending_booking(
            client, b2b_headers, admin_headers, b2c_headers
        )

        register_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Stranger",
                "surname": "User",
                "phone": "998922222222",
                "password": "password123",
                "role": "B2C",
            },
        )
        stranger_headers = {"Authorization": f"Bearer {register_resp.json()['access_token']}"}

        resp = await client.get(f"/api/v1/bookings/{booking_id}", headers=stranger_headers)
        assert resp.status_code == 403

    async def test_client_cannot_confirm_own_booking(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        booking_id = await self._create_pending_booking(
            client, b2b_headers, admin_headers, b2c_headers
        )

        resp = await client.post(f"/api/v1/bookings/{booking_id}/confirm", headers=b2c_headers)
        assert resp.status_code == 403

    async def test_non_owner_host_cannot_confirm(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        booking_id = await self._create_pending_booking(
            client, b2b_headers, admin_headers, b2c_headers
        )

        register_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Other",
                "surname": "Host",
                "phone": "998933333333",
                "password": "password123",
                "role": "B2B",
            },
        )
        other_host_headers = {"Authorization": f"Bearer {register_resp.json()['access_token']}"}

        resp = await client.post(
            f"/api/v1/bookings/{booking_id}/confirm", headers=other_host_headers
        )
        assert resp.status_code == 403

    async def test_non_client_cannot_cancel(
        self, client: AsyncClient, b2b_headers: dict, admin_headers: dict, b2c_headers: dict
    ):
        booking_id = await self._create_pending_booking(
            client, b2b_headers, admin_headers, b2c_headers
        )

        resp = await client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=b2b_headers)
        assert resp.status_code == 403
