"""Bron narxi va bekor qilish siyosati bo'yicha qaytarish — pure functions, DB'siz.

Frontend porti: src/components/BookingPanel.tsx (countNights), src/lib/promotions.ts,
src/lib/promoCodes.ts, src/lib/refund.ts.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

DEFAULT_PREPAY_PERCENT = 15
# date.weekday(): Mon=0..Sun=6. Dam olish = Juma/Shanba/Yakshanba — JS
# getDay()===0(Sun)||5(Fri)||6(Sat) bilan bir xil kunlarga to'g'ri keladi.
WEEKEND_WEEKDAYS = frozenset({4, 5, 6})

PROMO_CODES: dict[str, dict] = {
    "SAYOHAT10": {"type": "percent", "value": 10, "label": "-10% chegirma"},
    "YANGIUZ": {"type": "fixed", "value": 50_000, "label": "-50 000 so'm chegirma"},
    "DAM15": {"type": "percent", "value": 15, "label": "-15% chegirma"},
}


@dataclass
class NightsBreakdown:
    weekdays: int
    weekends: int
    season_nights: int
    season_extra: float


def count_nights(
    check_in: date,
    check_out: date,
    weekday_price: float,
    weekend_price: float,
    season_months: list[int],
    season_coef: float,
) -> NightsBreakdown:
    """`season_months` 0-indekslangan (0=Yanvar...11=Dekabr), frontenddagi kabi."""
    weekdays = weekends = season_nights = 0
    season_extra = 0.0
    cur = check_in
    while cur < check_out:
        is_weekend = cur.weekday() in WEEKEND_WEEKDAYS
        night_base = weekend_price if is_weekend else weekday_price
        if is_weekend:
            weekends += 1
        else:
            weekdays += 1
        if season_coef > 0 and (cur.month - 1) in season_months:
            season_nights += 1
            season_extra += round(night_base * season_coef / 100)
        cur += timedelta(days=1)
    return NightsBreakdown(weekdays, weekends, season_nights, season_extra)


def best_promotion(promotions: dict | None, days_until: int, nights: int) -> dict | None:
    """Bir nechta aksiya shartga mos kelsa — eng katta foizlisi (birlashtirilmaydi)."""
    if not promotions:
        return None
    opts: list[dict] = []
    early_bird = promotions.get("earlyBird")
    if early_bird and days_until >= early_bird["days"]:
        percent = early_bird["percent"]
        opts.append({"percent": percent, "label": f"Erta bron −{percent}%"})
    last_minute = promotions.get("lastMinute")
    if last_minute and 0 <= days_until <= last_minute["days"]:
        percent = last_minute["percent"]
        opts.append({"percent": percent, "label": f"So'nggi daqiqa −{percent}%"})
    long_stay = promotions.get("longStay")
    if long_stay and nights >= long_stay["nights"]:
        percent = long_stay["percent"]
        opts.append({"percent": percent, "label": f"Uzoq qolish −{percent}%"})
    if not opts:
        return None
    return max(opts, key=lambda o: o["percent"])


@dataclass
class PromoResult:
    ok: bool
    discount: float
    final: float
    label: str | None = None


def apply_promo(total: float, code: str | None) -> PromoResult:
    if not code or total <= 0:
        return PromoResult(ok=False, discount=0, final=total)
    promo = PROMO_CODES.get(code.strip().upper())
    if not promo:
        return PromoResult(ok=False, discount=0, final=total)
    raw = round(total * promo["value"] / 100) if promo["type"] == "percent" else promo["value"]
    discount = min(raw, total)
    return PromoResult(ok=True, discount=discount, final=total - discount, label=promo["label"])


def advance_of(total: float, prepay_percent: int) -> float:
    return round(total * prepay_percent / 100)


def remainder_of(total: float, prepay_percent: int) -> float:
    return total - advance_of(total, prepay_percent)


@dataclass
class BookingQuote:
    weekdays: int
    weekends: int
    weekday_sum: float
    weekend_sum: float
    season_nights: int
    season_extra: float
    promo_label: str | None
    promo_amount: float
    subtotal: float
    code_discount: float
    total: float
    prepay_percent: int
    advance: float
    remainder: float
    min_stay: int
    blocked_in_range: list[str]
    over_capacity: bool


def quote(
    listing,
    check_in: date,
    check_out: date,
    guests: int,
    promo_code: str | None,
    today: date,
) -> BookingQuote:
    extra = listing.extra or {}
    nights_info = count_nights(
        check_in,
        check_out,
        float(listing.weekday_price),
        float(listing.weekend_price),
        extra.get("highSeasonMonths") or [],
        extra.get("seasonCoef") or 0,
    )
    weekday_sum = nights_info.weekdays * float(listing.weekday_price)
    weekend_sum = nights_info.weekends * float(listing.weekend_price)
    subtotal = weekday_sum + weekend_sum + nights_info.season_extra
    nights = nights_info.weekdays + nights_info.weekends

    days_until = (check_in - today).days
    promo = best_promotion(extra.get("promotions"), days_until, nights)
    promo_amount = round(subtotal * promo["percent"] / 100) if promo else 0
    after_promo = subtotal - promo_amount

    code_result = apply_promo(after_promo, promo_code)
    total = code_result.final if code_result.ok else after_promo
    prepay_percent = extra.get("prepayPercent", DEFAULT_PREPAY_PERCENT)

    min_stay = max(1, extra.get("minStay") or 1)
    blocked = extra.get("blockedDates") or []
    check_in_s, check_out_s = check_in.isoformat(), check_out.isoformat()
    blocked_in_range = sorted(d for d in blocked if check_in_s <= d < check_out_s)

    return BookingQuote(
        weekdays=nights_info.weekdays,
        weekends=nights_info.weekends,
        weekday_sum=weekday_sum,
        weekend_sum=weekend_sum,
        season_nights=nights_info.season_nights,
        season_extra=nights_info.season_extra,
        promo_label=promo["label"] if promo else None,
        promo_amount=promo_amount,
        subtotal=subtotal,
        code_discount=code_result.discount if code_result.ok else 0,
        total=total,
        prepay_percent=prepay_percent,
        advance=advance_of(total, prepay_percent),
        remainder=remainder_of(total, prepay_percent),
        min_stay=min_stay,
        blocked_in_range=blocked_in_range,
        over_capacity=guests > listing.capacity,
    )


# ── Bekor qilishda qaytarish (guest/host) ──


def _policy_kind(policy: str | None) -> str:
    p = policy or ""
    if "Qaytarilmaydi" in p:
        return "nonref"
    if "Qattiq" in p:
        return "strict"
    if "Moslashuvchan" in p:
        return "flexible"
    return "moderate"


@dataclass
class RefundResult:
    percent: int
    amount: float
    burnt: float
    reason: str


def guest_refund(
    policy: str | None,
    check_in: date,
    advance: float,
    now: datetime | None = None,
) -> RefundResult:
    """Mijoz bekor qilganda avansdan qancha qaytishini hisoblaydi.

    `now` — faqat testlar uchun ixtiyoriy, berilmasa joriy UTC vaqt ishlatiladi
    (frontenddagi `now: Date = new Date()` default-parametr patterniga mos).
    """
    now = now or datetime.now(UTC)
    kind = _policy_kind(policy)
    check_in_dt = datetime.combine(check_in, time(14, 0), tzinfo=UTC)  # standart check-in 14:00
    hours = (check_in_dt - now).total_seconds() / 3600
    days = hours / 24

    if kind == "flexible":
        if hours >= 24:
            percent, reason = 100, "24 soatdan ko'p qolgan — avans to'liq qaytadi"
        else:
            percent, reason = 0, "24 soatdan kam qolgan — avans qaytmaydi"
    elif kind == "strict":
        if days >= 7:
            percent, reason = 100, "7 kundan ko'p qolgan — avans to'liq qaytadi"
        else:
            percent, reason = 0, "7 kundan kam qolgan — avans qaytmaydi"
    elif kind == "nonref":
        percent, reason = 0, "Qaytarilmaydigan tarif — avans qaytmaydi"
    else:  # moderate
        if days >= 3:
            percent, reason = 100, "3 kundan ko'p qolgan — avans to'liq qaytadi"
        elif days >= 1:
            percent, reason = 50, "1–3 kun qolgan — avansning 50% qaytadi"
        else:
            percent, reason = 0, "1 kundan kam qolgan — avans qaytmaydi"

    amount = round(advance * percent / 100)
    return RefundResult(percent=percent, amount=amount, burnt=advance - amount, reason=reason)


def host_reject_refund(advance: float) -> RefundResult:
    return RefundResult(
        percent=100, amount=advance, burnt=0, reason="Egasi rad etdi — avans to'liq qaytadi"
    )
