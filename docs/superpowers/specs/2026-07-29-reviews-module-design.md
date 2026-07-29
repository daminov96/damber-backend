# Reviews moduli — dizayn

**Sana**: 2026-07-29
**Holat**: Taklif (foydalanuvchi tasdig'ini kutmoqda)

## Kontekst

`guides`dan keyingi bosqich. `Listing`/`Tour`/`TourOperator`/`Guide`/`RentCompany`ning barchasida `rating`/`rating_count` maydonlari bor, lekin hozirgacha barchasi statik `0` — hech qayerda yozilmaydi.

Frontend tadqiqoti shuni tasdiqladi: **faqat Listings uchun ishlaydigan yozish yo'li mavjud** (`useReviews` do'koni, `ReviewModal.tsx`, `ListingReviews.tsx`, `RatingBreakdown.tsx`). Tours'da `reviews?: Review[]` maydoni bor, lekin **butunlay statik** (faqat seed ma'lumotda, yozish yo'li yo'q). Operators/Guides/RentCompanies'da sharh tushunchasi **umuman yo'q** (na maydon, na UI). Va eng muhimi: **`rating`/`ratingCount` sharhlar bilan hech qachon qayta hisoblanmaydi** — bu Guide'dagi `certified` bayrog'iga o'xshash "jonli ko'ringan, aslida statik" holat.

## Loyihachi qarorlar

- **Doira: faqat Listing va Tour.** Operators/Guides/RentCompanies uchun sharh UI/tushunchasi frontendda mutlaqo yo'q (bo'sh `rating` maydonidan boshqa hech narsa) — bu joyda kengaytirish mahsulot doirasini o'zimdan o'ylab topish bo'lardi, shuning uchun qilinmaydi. Tours esa `Review` turi/`RatingBreakdown`/`subScores` bilan bir xil, generic komponentlarga ega (faqat yozish yo'li ulanmagan) — shuning uchun qamrovga kiradi.
- **Polimorfik nishon — ikkita ixtiyoriy FK + CHECK constraint, `target_type` string emas.** Tours modulida `operator_id`/`guide_id` uchun qo'llanilgan aynan shu naqsh: `listing_id`/`tour_id` (ikkalasi ham ixtiyoriy, DB darajasida "aynan bittasi" CHECK). Bu haqiqiy FK (referential integrity, CASCADE) beradi — `target_type + target_id` (string+UUID) polimorfizmiga qaraganda ancha xavfsizroq (bunda FK constraint umuman bo'lmaydi).
- **Listing sharhi — MAJBURIY ravishda yakunlangan bronga bog'lanadi (server tomonda haqiqiy tekshiruv).** Frontendda bu niyat aniq ko'rinadi (dashboard'dagi "Baholash" tugmasi faqat `Yakunlandi` holatida yoqiladi, `verified` bayrog'i xuddi shuni tekshiradi) — **lekin hech qayerda majburiy qilinmagan** (listing sahifasidan har qanday user istalgan listingga sharh yoza oladi). Bu — aniq amalga oshirilmagan, lekin niyat sifatida aniq mahsulot qoidasi, backend'da **haqiqiy** qilib amalga oshiriladi: sharh yozish uchun `booking_id` majburiy, backend shu bron mijozga tegishli, shu listingga tegishli va `status == completed` ekanini tekshiradi. Bitta bronga faqat bitta sharh (`booking_id` — noyob).
- **Tour sharhi — bronga bog'lanmaydi.** `TourBooking.status`da "yakunlandi" tushunchasi umuman yo'q (faqat `pending`/`confirmed`/`rejected`) — shuning uchun "yakunlangan safar"ni tekshirishning ishonchli usuli yo'q. Soxta tekshiruv o'ylab topish o'rniga (masalan "confirmed"ni yakunlangan deb hisoblash — noto'g'ri bo'lardi), tur sharhi **istalgan avtorizatsiyalangan foydalanuvchi** tomonidan yozilishi mumkin, `verified` doim `false`. Bitta foydalanuvchi bitta turga faqat bitta sharh yoza oladi (`client_id`+`tour_id` — noyob, spam'dan himoya).
- **`rating`/`rating_count` — serverda, sharh yaratilganda/tahrirlanganda/o'chirilganda qayta hisoblanadi.** Frontendda bu hech qachon bo'lmagan — shuning uchun "mavjud xatti-harakatni saqlash" emas, "buzilgan kutishni tuzatish". Qayta hisoblash mantig'i **nishon modulining o'zida** joylashadi (`listings/service.py::recompute_rating()`, `tours/service.py::recompute_rating()`) — Reviews moduli faqat shu tor funksiyalarni chaqiradi, Listing/Tour'ning ichki holatini to'g'ridan-to'g'ri o'zgartirmaydi (modul chegaralarini hurmat qilish — RentCompanies spec'idagi "listings o'z mantig'ini saqlaydi" tamoyili bilan bir xil).
- **`sub_scores` — 5 ta belgilangan kategoriya bilan cheklanadi.** Frontend `SUBSCORE_CATEGORIES` — aniq 5 ta qiymat (`cleanliness`, `location`, `service`, `value`, `comfort`). Backend schema darajasida shu ro'yxatdan tashqari kalitlarni rad etadi (frontenddagi cheklanmagan `Record&lt;string, number&gt;`dan ko'ra qattiqroq — bu erkin matn kaliti xavfsizlik/ma'lumot sifatini yomonlashtirar edi).
- **Tahrirlash — ID bo'yicha, indeks bo'yicha emas.** Frontend `updateReview(listingId, idx, ...)` — massiv indeksi bo'yicha, `Review`da `id` umuman yo'q. Bu ishonchsiz (indekslar surilishi mumkin). Backend har doim UUID `id` bilan ishlaydi (standart CRUD).
- **O'chirish qo'shiladi — frontendda yo'q.** Frontendda `deleteReview` umuman yo'q. Ammo bu — Listings/Operators/Tours/Guides/RentCompanies'ning barchasida mavjud standart CRUD imkoniyati (o'z sharhini yoki ADMIN har qanday sharhni o'chira olishi) — bu izchillik uchun qo'shiladi.

## Ma'lumotlar modeli

`app/modules/reviews/models.py`:

```python
class Review(Base):
    __tablename__ = "reviews"

    __table_args__ = (
        CheckConstraint(
            "(listing_id IS NOT NULL AND tour_id IS NULL) OR "
            "(listing_id IS NULL AND tour_id IS NOT NULL)",
            name="ck_reviews_exactly_one_target",
        ),
        UniqueConstraint("client_id", "tour_id", name="uq_reviews_client_tour"),
    )

    id: UUID (pk)
    client_id: UUID (FK users.id, index)
    listing_id: UUID | None (FK listings.id, ondelete="CASCADE", index)
    tour_id: UUID | None (FK tours.id, ondelete="CASCADE", index)
    booking_id: UUID | None (FK bookings.id, unique=True, index)   # faqat listing sharhida to'ladi

    stars: int                                    # 1–5 (schema)
    text: str(2000)
    sub_scores: dict (JSONB) default=dict          # {"cleanliness": 5, ...} — 5 kalitdan tashqarisi rad etiladi
    verified: bool default=False                    # listing+booking bo'lsa har doim True, tour uchun har doim False

    created_at: DateTime server_default=func.now()
    updated_at: DateTime | None                      # PATCH qilinganda yoziladi
```

`UniqueConstraint("client_id", "tour_id", ...)` — `tour_id` `NULL` bo'lgan qatorlarda (ya'ni listing sharhlari) Postgres standart bo'yicha bir nechta `NULL`ga ruxsat beradi, shuning uchun bu cheklov listing sharhlariga ta'sir qilmaydi, faqat tur sharhlarida "bitta user — bitta tur — bitta sharh"ni ta'minlaydi.

## Endpoints

Prefix `/api/v1`:

| Method | Path | Kim | Tavsif |
|---|---|---|---|
| GET | `/reviews` | har kim | `listing_id` YOKI `tour_id` (aynan bittasi, query param), `page, page_size` — eng yangisi birinchi |
| GET | `/reviews/mine` | `CurrentUser` | O'z yozgan sharhlari |
| POST | `/reviews` | `CurrentUser` | Yaratadi — pastga qarang |
| PATCH | `/reviews/{id}` | egasi | `stars`/`text`/`sub_scores` tahrirlash |
| DELETE | `/reviews/{id}` | egasi/ADMIN | O'chirish |

**`POST /reviews` validatsiyasi** (`ReviewCreateRequest`): `listing_id: UUID | None`, `tour_id: UUID | None`, `booking_id: UUID | None`, `stars: int (1-5)`, `text (min 10 belgi)`, `sub_scores: dict[str, int] = {}`.
- `model_validator`: `listing_id`/`tour_id`dan aynan bittasi.
- `listing_id` berilganda `booking_id` **majburiy** (`model_validator`).
- `tour_id` berilganda `booking_id` berilmasligi kerak (mantiqiy emas — rad etiladi).

## Service funksiyalari (`app/modules/reviews/service.py`)

- `create(db, client, payload)`:
  - Listing sharhi: `booking = get bookings.Booking by id`; `booking.client_id != client.id` → 403; `booking.listing_id != payload.listing_id` → 400; `booking.status != BookingStatus.completed` → 409 ("Faqat yakunlangan bron uchun sharh qoldirish mumkin"); `booking_id` allaqachon sharhlangan bo'lsa (unique constraint) → 409 ("Bu bron allaqachon baholangan"); `verified=True`.
  - Tur sharhi: `(client_id, tour_id)` juftligi mavjudligini oldindan tekshiradi → 409 ("Siz bu turga allaqachon sharh qoldirgansiz"); `verified=False`.
  - Yaratilgach: `await listings_service.recompute_rating(db, listing_id)` YOKI `await tours_service.recompute_rating(db, tour_id)`.
- `update(db, review_id, current_user, payload)`: faqat muallif (`client_id == current_user.id`) — ADMIN ham tahrirlay olmaydi (sharh matni ADMINga tegishli emas, faqat o'chirish huquqi bor). Yangilagach nishonning reytingini qayta hisoblaydi.
- `delete(db, review_id, current_user)`: muallif yoki ADMIN. O'chirgach reytingni qayta hisoblaydi.
- `list_for_target(db, listing_id, tour_id, page, page_size)`, `list_mine(db, client, page, page_size)`.

`app/modules/listings/service.py`ga qo'shiladi:
```python
async def recompute_rating(db: AsyncSession, listing_id: uuid.UUID) -> None:
    stmt = select(func.avg(Review.stars), func.count(Review.id)).where(Review.listing_id == listing_id)
    avg, count = (await db.execute(stmt)).one()
    listing = await _get_or_404(db, listing_id)
    listing.rating = round(float(avg), 2) if avg is not None else 0
    listing.rating_count = count
    await db.commit()
```
`app/modules/tours/service.py`ga xuddi shu shakldagi `recompute_rating()` qo'shiladi (`Review.tour_id` bilan).

**Aylanma import haqida eslatma**: `listings/service.py` va `tours/service.py` endi `reviews.models.Review`ni import qiladi; `reviews/service.py` esa `listings.models`/`tours.models`/`bookings.models`ni import qiladi. Bu — modellar darajasida aylanma emas (`Review` modeli hech narsani import qilmaydi, faqat `service.py`lar bir-birining modellarini chaqiradi) — bookings/operators/tours orasida allaqachon o'rnatilgan xavfsiz naqsh.

## Test strategiyasi

`tests/test_reviews.py`:
1. Listing sharhi — yakunlangan bron bilan muvaffaqiyatli, `verified=True`, `listing.rating`/`rating_count` to'g'ri yangilanadi
2. Listing sharhi — `booking_id` berilmasa 422; bron boshqa userga tegishli bo'lsa 403; bron `pending`/`confirmed` holatda bo'lsa 409; bron boshqa listingga tegishli bo'lsa 400
3. Bitta bronga ikkinchi marta sharh — 409
4. Tur sharhi — bronsiz, istalgan user, muvaffaqiyatli, `verified=False`
5. Bitta user bitta turga ikkinchi marta sharh — 409
6. `sub_scores`da noma'lum kalit — 422
7. Tahrirlash — faqat muallif; tahrirlagach reyting qayta hisoblanadi
8. O'chirish — muallif/ADMIN; o'chirgach reyting qayta hisoblanadi (masalan yagona sharh o'chirilsa `rating=0, rating_count=0`ga qaytadi)
9. `GET /reviews` — `listing_id`/`tour_id` filtri, sahifalab

## Migratsiya

`alembic revision --autogenerate -m "reviews jadvali"`. CHECK constraint (operators/tours tajribasiga ko'ra) qo'lda qo'shiladi.

## Doiradan tashqari

- Operators/Guides/RentCompanies uchun sharhlar (frontendda tushuncha yo'q)
- Xost javobi (host reply) — frontendda yo'q
- Sharh uchun rasm yuklash — frontendda yo'q
