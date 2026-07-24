# Listings moduli — dizayn

**Sana**: 2026-07-24
**Holat**: Tasdiqlangan

## Kontekst

Frontend (`D:\projects\dam\front\last\damber-front`) hozircha to'liq localStorage-mock holatida ishlaydi — haqiqiy backend API chaqiruvi yo'q. `src/lib/api.ts` ataylab integration seam sifatida qoldirilgan, va Zustand store'lar (`src/store/myListings.ts`, `src/store/listingManage.ts`) hamda `src/lib/types.ts`dagi `Listing` interfeysi kerakli backend contract'ni aniq ko'rsatib turibdi.

Backend'da (`D:\projects\dam\backend`) hozircha faqat `users` moduli tayyor (register/login/me, JWT, rol: B2C/B2B/ADMIN). `listings`, `bookings`, `wallet` modullari bo'sh skelet.

Bu spec — **Listings moduli**ni qamrab oladi (frontend'ning eng markaziy domeni). Bookings, Wallet, Tours/Operators, Chat, Admin, Plans — alohida keyingi speclar bo'ladi.

## Ma'lumotlar modeli

Bitta `listings` jadvali, umumiy ustunlar + moslashuvchan JSONB, frontend'ning `Listing` interfeysiga 1:1 mos:

**Haqiqiy ustunlar** (`app/modules/listings/models.py`):
- `id: UUID` (PK)
- `owner_id: UUID` (FK → users.id)
- `name: str`
- `type: Enum(ListingType)` — Dacha, Hotel, Boutique, Hostel, Recreation, Camping, Villa, Sanatorium, RentCar, Dining
- `region: Enum(Region)` — 17 ta viloyat/shahar (Bostanliq, Zomin, Khiva, Samarkand, Bukhara, Tashkent, ToshkentViloyat, Namangan, Andijan, Fergana, Surkhandarya, Kashkadarya, Navoi, Syrdarya, Jizzakh, Khorezm, Karakalpakstan)
- `weekday_price: Numeric(14,2)`
- `weekend_price: Numeric(14,2)`
- `rating: float`, `rating_count: int` — default 0
- `verified: bool` — default `false`
- `paused: bool` — default `false`
- `capacity: int`
- `amenities: ARRAY(String)` — `Amenity` enum qiymatlaridan (40+ ta, frontend `types.ts`dagi ro'yxat)
- `description: str`
- `license: str | None`, `license_expiry: date | None`
- `views: int`, `saves: int` — default 0
- `is_hot: bool` — default `false`
- `discount: int` — default 0
- `created_at: datetime`

**Moslashuvchan maydonlar** — `extra: JSONB` ustunida: `roomTypes, promotions, rules, typeExtras, blockedDates, highSeasonMonths, seasonCoef, prepayPercent, customAmenities, guestTypes, landmark, roomsTotal, checkIn, checkOut, minStay, earlyCheckIn, minGuests, childrenAllowed, address, coords, locationLink, serviceFee, longStayDiscount, extraNotes, contactPhone, contactEmail, tin, socialLink, socialLinks, fax, district, companyId, starRating, videoUrl`.

**Fotosuratlar** — alohida jadval:
```
listing_photos
  id: UUID (PK)
  listing_id: UUID (FK → listings.id, CASCADE delete)
  url: str
  position: int
```

## Storage abstraction

```python
class StoragePort(Protocol):
    async def save(self, file: UploadFile, subdir: str) -> str: ...  # public URL qaytaradi
    async def delete(self, url: str) -> None: ...
```

Boshlang'ich adapter: `LocalDiskStorage` — `/app/uploads/<subdir>/<uuid>.<ext>` ga saqlaydi, `/static/uploads` orqali xizmat qiladi (Docker named volume: `damber_uploads:/app/uploads`).

Kelajakda MinIO/S3 adapteriga o'tish — faqat yangi klass yozib, DI'da almashtirish orqali, router/service kodiga tegilmaydi.

**Cheklovlar**: bitta listingga maksimal 10 ta rasm, har biri 5MB gacha, format: jpg/png/webp.

## Endpoints

Prefix: `/api/v1`, `app/modules/listings/router.py`

| Method | Path | Ruxsat | Tavsif |
|---|---|---|---|
| GET | `/listings` | Public | Qidiruv/filtr/pagination. Faqat `verified=true and paused=false` qaytadi |
| GET | `/listings/{id}` | Public (owner/ADMIN uchun unverified ham) | Bitta listing |
| GET | `/listings/mine` | B2B (owner) | O'zining barcha listinglari, holatidan qat'iy nazar |
| POST | `/listings` | B2B | Yangi listing, `verified=false` bilan boshlanadi |
| PATCH | `/listings/{id}` | Owner yoki ADMIN | Qisman yangilash |
| DELETE | `/listings/{id}` | Owner yoki ADMIN | O'chirish (bog'liq photos storage'dan ham o'chadi) |
| POST | `/listings/{id}/pause` | Owner | `paused` toggle |
| POST | `/listings/{id}/photos` | Owner | Multipart upload (bir yoki bir nechta fayl) |
| DELETE | `/listings/{id}/photos/{photo_id}` | Owner | Bitta rasmni o'chirish |
| POST | `/admin/listings/{id}/approve` | ADMIN | `verified=true` qiladi |

**Qidiruv parametrlari** (`GET /listings`):
`type, region, min_price, max_price, amenities (repeatable), guests, sort (price_asc|price_desc|rating|newest|hot|most_saved), page, page_size`

## Ruxsat va validatsiya qoidalari

- Yaratish/tahrirlash/o'chirish — faqat `owner_id == current_user.id` yoki `role == ADMIN` (aks holda `ForbiddenError`, mavjud `app/core/exceptions.py`dan)
- `weekday_price`, `weekend_price`, `capacity` > 0
- `type` va `region` — belgilangan enum qiymatlaridan
- `amenities` — ruxsat etilgan `Amenity` enum ro'yxatidan tashqari qiymat rad etiladi
- Mavjud helper'lar: `NotFoundError`, `ConflictError`, `ForbiddenError`, `UnauthorizedError`, `require_role()` — yangi xatolik turi kerak emas

## Test strategiyasi

Repo'da hali test yo'q. Seam: HTTP router darajasida (`httpx.AsyncClient` + FastAPI test app) — auth, DB, validatsiya birgalikda sinaladi. Test DB: alohida Postgres (enum/array Postgres-specific bo'lgani uchun SQLite ishlatilmaydi), har test uchun transaction rollback fixture.

Qamrov (vertikal slice, TDD tartibida yoziladi):
1. B2B register → login → `POST /listings` → `verified=false`
2. `GET /listings` — unverified listing ko'rinmaydi
3. ADMIN `POST /admin/listings/{id}/approve` → endi `GET /listings`da ko'rinadi
4. B2C boshqa userning listing'ini PATCH qila olmaydi (403)
5. Owner PATCH/DELETE qila oladi
6. Qidiruv filtrlari (type, region, price range, amenities) to'g'ri natija beradi
7. Photo upload/delete

## Migratsiya

`alembic revision --autogenerate -m "listings jadvali"`, oldindan `migrations/env.py`ga `app.modules.listings.models` importi qo'shiladi.

## Docker o'zgarishlari

- `docker-compose.yml`: yangi named volume `damber_uploads:/app/uploads`
- `app/main.py`: `app.mount("/static/uploads", StaticFiles(directory="uploads"))`

## Doiradan tashqari (keyingi speclar)

- Bookings moduli (escrow, cancellation policy, refund)
- Wallet moduli (balance, topup, transfer)
- Tours / Tour Operators / Tour Bookings
- Rent-car kompaniyalari
- Reviews
- Chat
- Admin moderatsiya paneli (to'liq — bu specda faqat approve endpoint bor)
- Plans/Subscriptions
- MinIO/S3'ga o'tish
