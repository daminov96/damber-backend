# Bookings moduli — dizayn

**Sana**: 2026-07-28
**Holat**: Taklif (foydalanuvchi tasdig'ini kutmoqda)

## Kontekst

Bu spec yozishdan oldin frontend manbasi (`.../front/front2807/damber-front/`, mahalliy `git log` bo'yicha eng so'nggi holat) to'liq o'qib chiqildi, chunki bookings — loyihaning eng murakkab domeni va frontend allaqachon aniq qoidalar bilan ishlab chiqilgan (prototip emas, qat'iy spesifikatsiya):

- `src/lib/refund.ts` — avans/eskrov modeli va bekor qilish siyosati bo'yicha qaytarish (`guestRefund`, `hostRejectRefund`)
- `src/components/booking/PaymentStep.tsx` — to'lov FAQAT DamBer hamyoni orqali
- `src/components/booking/BookingModal.tsx` — bron yaratish oqimi, `cancellationPolicy: listing.rules?.cancellation` nusxalanishi
- `src/store/auth.ts` — `createBooking/setBookingStatus/releaseEscrow/cancelBooking/restoreBooking` — to'liq state machine
- `src/components/BookingPanel.tsx`, `src/lib/promotions.ts`, `src/lib/promoCodes.ts` — narx hisoblash (hafta ichi/dam olish tunlari, mavsumiy ustama, aksiyalar, promo kod)
- `src/lib/availability.ts` — band kunlar va minimal tun tekshiruvi
- `src/components/host/HostBookingsTab.tsx` — xost tomonidagi amallar va ularning UI shartlari (qaysi tugma qachon ko'rinadi)

Ikkita oldin ochiq qolgan savol frontend kodidan **tasdiqlandi** (taxmin emas):

1. **Avans to'lovi faqat wallet** — boshqa yo'l yo'q, balans yetmasa bloklanadi.
2. **Cancellation policy listing'dan nusxalanadi** — bron yaratilganda `listing.extra`dagi qiymatdan o'qilib bookingga yoziladi, keyin listing o'zgarsa ham booking siyosati o'zgarmaydi.

Bundan tashqari muhim topilma: **avans foizi qat'iy 15% emas** — `listing.prepayPercent` (0/15/30/100%, standart 15), shuningdek narx `weekday_price`/`weekend_price`, mavsumiy ustama (`highSeasonMonths`/`seasonCoef`) va aksiyalar (`promotions.earlyBird/lastMinute/longStay`) ham listing'ga bog'liq. Backend `Listing` modelida bularning barchasi uchun alohida ustun yo'q — ular `listing.extra` (JSONB) ichida saqlanadi (`app/modules/listings/models.py:146`), xuddi wizard to'ldiradigan boshqa ixtiyoriy maydonlar kabi.

## Loyihachi qarorlari (frontend prototipida yo'q, backend uchun qo'shiladi)

Frontend — localStorage-mock prototip, real pul harakati va concurrent foydalanuvchilar yo'q. Backend real bo'lgani uchun quyidagi qo'shimchalar zarur, ammo frontend mantig'iga zid emas:

- **Narxni server qayta hisoblaydi** — clientdan kelgan `total`ga ishonilmaydi (pul harakati bor joyda bu xavfsizlik talabi). `POST /bookings`da backend narxni frontend bilan bir xil formula bo'yicha o'zi hisoblaydi.
- **`GET /bookings/quote`** — yangi endpoint, bron yaratishdan oldin narx breakdown'ini oldindan ko'rsatish uchun (frontend keyingi bosqichda shu API'ga ulanadi — `BookingPanel.tsx`dagi `calc` shu yerdan keladi).
- **Kesishgan bronlarni bloklash** — frontend faqat `listing.blockedDates` (xost qo'lda belgilagan) tekshiradi, mavjud bronlar bilan kesishishni tekshirmaydi. Backend qo'shimcha ravishda: bir listing uchun sanalari kesishgan **faol** (`pending`/`confirmed`) boshqa booking bo'lsa — 409.
- **Race condition himoyasi** — bron yaratishda `Listing` qatori `SELECT ... FOR UPDATE` bilan qulflanadi (wallet modulidagi `_lock_user` patterniga o'xshash), shu bilan bir vaqtda kelgan ikkita so'rov bir xil sanalarga qo'sh bron qo'ya olmaydi.
- **Ko'p xonali obyektlar (roomTypes) — doiradan tashqari.** Backend `Listing`da hali xona turlari first-class emas (faqat `extra` ichida). V1'da booking narxi to'g'ridan-to'g'ri `listing.weekday_price`/`weekend_price`dan hisoblanadi; xona tanlash keyingi bosqichda (Listings moduliga roomTypes qo'shilgach).
- **`wallet.service`ga kichik qo'shimcha**: hozirgi `transfer()` faqat ikki tomonlama (debit+kredit) ishlaydi, lekin eskrov release/refund/reject holatlarida faqat **bir tomonlama kredit** kerak (chunki debit booking yaratilganda allaqachon bo'lgan). Shu sabab `credit()` funksiyasi ajratiladi, `transfer()` esa `pay()+credit()`ga refaktor qilinadi (xatti-harakat o'zgarmaydi).

## Ma'lumotlar modeli

`app/modules/bookings/models.py`:

```python
class BookingStatus(enum.StrEnum):
    pending = "pending"      # Kutilmoqda
    confirmed = "confirmed"  # Tasdiqlandi
    completed = "completed"  # Yakunlandi
    rejected = "rejected"    # Rad etildi
    cancelled = "cancelled"  # Bekor qilindi

class EscrowStatus(enum.StrEnum):
    held = "held"
    released = "released"
    refunded = "refunded"

class CancelledBy(enum.StrEnum):
    guest = "guest"
    host = "host"

class Booking(Base):
    __tablename__ = "bookings"
    id: UUID (pk)
    listing_id: UUID (FK listings.id, index)
    client_id: UUID (FK users.id, index)
    owner_id: UUID (FK users.id, index)         # booking yaratilganda listing.owner_iddan nusxalanadi
    check_in: Date
    check_out: Date
    guests: Integer
    status: Enum(BookingStatus) default=pending
    total_amount: Numeric(14,2)
    advance_amount: Numeric(14,2) default=0
    prepay_percent: Integer                      # listing.extra.prepayPercentdan nusxalanadi (audit uchun)
    escrow: Enum(EscrowStatus) | None             # advance_amount=0 bo'lsa None
    cancellation_policy: str | None (500)         # listing.extra.rules.cancellationdan nusxalanadi
    promo_code: str | None (50)
    guest_name: str (150)
    guest_phone: str (20)
    guest_email: str | None (255)
    guest_type: str | None (50)
    message: str | None (1000)
    reject_reason: str | None (500)
    refund_amount: Numeric(14,2) | None
    cancelled_by: Enum(CancelledBy) | None
    confirmed_at: DateTime | None
    created_at: DateTime server_default=now
```

## Narx hisoblash (`app/modules/bookings/pricing.py`)

Frontenddagi `countNights` + `bestPromotion` + `applyPromo` ning to'g'ridan-to'g'ri Python porti (pure function, DB'siz):

- `count_nights(check_in, check_out, weekday_price, weekend_price, season_months, season_coef) -> NightsBreakdown` — `weekdays, weekends, season_nights, season_extra`. Dam olish kunlari = Juma/Shanba/Yakshanba (`date.weekday() in {4,5,6}`, JS `getDay()===0|5|6` bilan bir xil semantika).
- `best_promotion(promotions, days_until, nights) -> {percent, label} | None` — `earlyBird`/`lastMinute`/`longStay`dan eng katta foizlisi (birlashtirilmaydi).
- `apply_promo(total, code) -> PromoResult` — `PROMO_CODES` jadvali (`SAYOHAT10`, `YANGIUZ`, `DAM15`) frontenddagi bilan bir xil qiymatlarda ko'chiriladi.
- `quote(listing, check_in, check_out, guests, promo_code, today) -> BookingQuote` — yuqoridagilarni birlashtirib to'liq breakdown qaytaradi: `weekdays, weekends, weekday_sum, weekend_sum, season_nights, season_extra, promo_label, promo_amount, subtotal, code_discount, total, prepay_percent, advance, remainder, min_stay, blocked_in_range, over_capacity`. Bu funksiya `listing.extra`dan `highSeasonMonths/seasonCoef/promotions/prepayPercent/minStay/blockedDates` o'qiydi (`.get()` bilan, standart qiymatlar frontenddagiga mos: `prepayPercent` yo'q bo'lsa 15, `seasonCoef` yo'q bo'lsa 0 va h.k.).

## Endpoints

Prefix `/api/v1/bookings`, barchasi `CurrentUser` bilan himoyalangan:

| Method | Path | Kim | Tavsif |
|---|---|---|---|
| GET | `/bookings/quote` | har kim | Query: `listing_id, check_in, check_out, guests, promo_code?`. Narx oldindan ko'rish, booking yaratmaydi |
| POST | `/bookings` | mijoz | Bron yaratadi — narxni serverda qayta hisoblaydi, sana kesishuvi/min_stay/capacity tekshiradi, wallet'dan avansni yechadi (`escrow=held`), `status=pending` |
| GET | `/bookings/mine` | mijoz | O'zining bronlari (client sifatida), sahifalab |
| GET | `/bookings/host` | xost | O'z e'lonlariga tushgan bronlar, `status` bo'yicha filtr ixtiyoriy |
| GET | `/bookings/{id}` | client/owner/ADMIN | Bitta bron |
| POST | `/bookings/{id}/confirm` | xost | `pending → confirmed`, `confirmed_at` yoziladi |
| POST | `/bookings/{id}/reject` | xost | Faqat `pending`dan. `{reason?}`. Avans 100% mijozga qaytadi, `escrow: held → refunded`, `status=rejected` |
| POST | `/bookings/{id}/complete` | xost | Faqat `confirmed` + `escrow=held`dan. Avans egaga o'tadi, `escrow: held → released`, `status=completed` |
| POST | `/bookings/{id}/cancel` | mijoz | Faqat `pending`/`confirmed`dan. Siyosat-asosli qaytarish (`guest_refund`), qolgan qism egaga kompensatsiya, `status=cancelled` |
| POST | `/bookings/{id}/restore` | xost | Faqat `rejected`dan. Qaytarilgan summani mijoz hamyonidan qayta ushlaydi (balans yetmasa 409), `status=pending` |

## Service funksiyalari (`app/modules/bookings/service.py`)

- `quote(db, listing_id, check_in, check_out, guests, promo_code) -> BookingQuote` — listing'ni o'qiydi, `pricing.quote()` chaqiradi
- `create(db, client, payload) -> Booking` — listing qatorini qulflaydi (`with_for_update`), quote hisoblaydi, kesishgan faol bronlarni tekshiradi (409 "Bu sanalar band"), `min_stay`/`over_capacity`/`blocked_in_range` tekshiradi (400), `advance_amount > 0` bo'lsa `wallet.service.pay()` chaqiradi (balans yetmasa `ConflictError` shu yerdan ko'tariladi), booking yaratadi
- `get_by_id(db, booking_id, user) -> Booking` — faqat client/owner/ADMIN ko'ra oladi, aks holda `ForbiddenError`
- `list_mine(db, client, page, page_size)`, `list_for_host(db, owner, status, page, page_size)`
- `confirm(db, booking_id, host) -> Booking`
- `reject(db, booking_id, host, reason) -> Booking` — `wallet.service.credit(client, advance, kind=refund)`
- `complete(db, booking_id, host) -> Booking` — `wallet.service.credit(owner, advance, kind=booking)`
- `cancel(db, booking_id, client) -> Booking` — `pricing.guest_refund(cancellation_policy, check_in, advance, now)` portlanadi `refund.ts`dan; `amount`ni mijozga, `burnt`ni egaga kredit qiladi
- `restore(db, booking_id, host) -> Booking` — `wallet.service.pay(client, refund_amount)` (balans yetmasa `ConflictError`)

`wallet/service.py`ga qo'shiladi: `credit(db, user, amount, label, kind=other, ref=None) -> WalletTransaction` (bir tomonlama kredit, `_lock_user` ishlatadi); `transfer()` shu funksiyani chaqiradigan qilib refaktor qilinadi.

## Validatsiya

- `check_out > check_in`, `guests > 0`
- `guests <= listing.capacity` → 400 "Mehmonlar soni sig'imdan oshib ketdi"
- Tanlangan tunlar soni `min_stay`dan kam → 400
- Oraliqqa xost band qilgan kun tushsa (`listing.extra.blockedDates`) → 400
- Oraliq boshqa faol (`pending`/`confirmed`) booking bilan kesishsa → 409 "Bu sanalar band"
- Avans balansdan katta → 409 (wallet.service.pay orqali avtomatik)
- Status o'tishlari noto'g'ri bo'lsa (masalan `completed`ni qayta `confirm` qilish) → 409 "Bron holati bunga mos emas"

## Test strategiyasi

`tests/test_bookings.py`, mavjud `tests/conftest.py` fixture'laridan foydalanib:

1. `quote()` — hafta ichi/dam olish tunlari to'g'ri ajratiladi, mavsumiy ustama qo'shiladi, eng yaxshi aksiya tanlanadi, promo kod to'g'ri qo'llanadi
2. Booking yaratish — muvaffaqiyatli: wallet'dan avans yechiladi, `escrow=held`, `status=pending`
3. Booking yaratish — balans yetmasa → 409, booking yaratilmaydi, balans o'zgarmaydi
4. Booking yaratish — sanalar kesishsa → 409
5. Booking yaratish — band kun / min_stay / capacity buzilsa → 400
6. Xost tasdiqlaydi — `pending → confirmed`, `confirmed_at` yoziladi
7. Xost rad etadi — mijozga 100% qaytadi, `escrow=refunded`, `status=rejected`
8. Xost yakunlaydi (`complete`) — egaga avans o'tadi, `escrow=released`
9. Mijoz bekor qiladi — `guest_refund` tier'lari bo'yicha parametrlangan testlar (flexible/moderate/strict/nonref, turli vaqt oralig'i)
10. Xost rad etilgan bronni tiklaydi — mablag' qayta ushlanadi; balans yetmasa 409
11. Ruxsat tekshiruvlari — begona user o'zganing bronini ko'ra/boshqara olmaydi (403)

## Migratsiya

`alembic revision --autogenerate -m "bookings jadvali"`, oldindan `migrations/env.py`ga `app.modules.bookings.models` importi qo'shiladi.

## Doiradan tashqari (keyingi speclar)

- Ko'p xonali obyektlarda xona tanlab bron qilish (Listings'ga `roomTypes` first-class qo'shilgach)
- Real to'lov gateway (Click/Payme) — hozircha ham wallet topup, ham booking avansi "qo'lda" hisoblanadi
- Chat integratsiyasi (bron xabari xost bilan chatga tushishi — frontendda bor, backend Chat moduli hali yo'q)
- Avtomatik eslatma/SMS (frontendda soxta toast, backendda hozircha yo'q)