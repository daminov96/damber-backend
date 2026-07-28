# Tours moduli — dizayn

**Sana**: 2026-07-28
**Holat**: Taklif (foydalanuvchi tasdig'ini kutmoqda)

## Kontekst

`operators` modulidan keyingi bosqich. Foydalanuvchi bilan oldindan ikkita muhim savol hal qilindi:

1. **Tur bronlash modeli — oddiy so'rov (inquiry/lead-capture), to'lov/eskrov YO'Q.** Frontend tadqiqoti tasdiqladi: `TourBooking` (`src/store/tourBookings.ts`) — shunchaki ism/telefon/odam soni + `totalEstimate` (faqat ko'rsatish uchun hisoblangan, haqiqiy to'lov emas). `GatewaySim.tsx`, `refund.ts`, wallet eskrov mexanizmi tur bronlariga umuman bog'liq emas (grep bilan tasdiqlandi — 0 ta moslik). `TourCancellation.tsx` faqat statik matn, hech qanday hisoblash yo'q.
2. **Modullar ketma-ketligi**: Operators → **Tours** (hozir) → RentCompanies.

Tadqiqot manbalari: `src/lib/types.ts` (`Tour` interfeysi), `src/data/tours.ts`, `src/components/host/TourForm.tsx`/`TourManageModal.tsx`, `src/store/myTours.ts`, `src/components/TourBookingForm.tsx`, `src/store/tourBookings.ts`, `src/components/TourDetailView.tsx`, `src/lib/tourFilter.ts`.

## Loyihachi qarorlari

- **Moderatsiya — `pending: bool`, Listings'ga o'xshab ADMIN tasdiqlaydi.** Frontend'da `MyTour.pending: boolean` (yaratilganda `true`), `approve(id)` admin amali `pending: false` qiladi. Rad etish yo'q (faqat `remove()`). Backend xuddi shunday: `pending` default `True`, `POST /admin/tours/{id}/approve` (Listings'dagi `/admin/listings/{id}/approve` bilan bir xil pattern).
- **Murakkab ichki tuzilmalar (`itinerary`, `stops`, `price_tiers`, `departures`, `includes`/`excludes`, `faq`) — `extra` JSONB'da.** Bularning har birini alohida jadvalga normallashtirish (5+ bola jadval) katta murakkablik qo'shar edi. Listings moduli ham xuddi shu strategiyani qo'llagan — wizard'ga xos moslashuvchan maydonlar `extra: dict`da saqlanadi. Tours ham shunga amal qiladi: asosiy qidiriladigan/filtrlanadigan maydonlar alohida ustun, qolgan murakkab struktura `extra`da.
- **Aksiya/reklama to'lovi (`TourActivation.tsx`) — doiradan tashqari.** Frontend'da mavjud (Listings'dagi bilan bir xil `ActivationPhases`/`usePromoSelection` komponentlarini qayta ishlatadi, xost o'z turini reklama qilish uchun wallet'dan to'laydi). Ammo bu funksiya **Listings moduli uchun ham hali backend'da qurilmagan** (`listings/service.py`da `approve()`/`toggle_pause()` bor, lekin promo-to'lov yo'q) — shuning uchun bu yerda ham qamrovdan chiqariladi, izchillik uchun. Kelajakda ikkalasi uchun ham bitta umumiy "promotion" spec sifatida qo'shiladi.
- **Qidiruv — soddalashtirilgan.** Frontend'dagi `REGION_CITY_ALIASES` (qo'lda saqlanadigan, faqat 3 ta viloyat uchun shahar nomi ↔ viloyat moslashtirish xakati) va erkin matndan `duration`ni tahlil qilib "qisqa/o'rta/uzoq" toifalash — ikkalasi ham SQL filtriga qulay emas va prototip-darajasidagi yechim. Backend'da: `region` — aniq moslik; davomiylik bo'yicha filtr — allaqachon mavjud strukturaviy `nights: int | None` maydonidan (erkin matn `duration`ni tahlil qilish o'rniga).
- **Tahrirlash (`PATCH`) qo'shiladi — frontend'da yo'q, lekin qasddan emas.** Tadqiqot shuni ko'rsatdiki, `myTours.ts`da `update`/tahrirlash amali umuman yo'q — bu operatorlardagi "moderatsiya yo'q" kabi izchil qasddan qilingan qaror emas, balki tugallanmagan prototip UI (faqat qo'shish/tasdiqlash/o'chirish). Backend `listings`/`operators`dagi izchillik uchun `PATCH /tours/{id}` qo'shadi (egasi/ADMIN).
- **Tur bron so'rovi (`TourBooking`) — status o'tishlari qo'shiladi.** Frontend turi (`Kutilmoqda`/`Tasdiqlandi`/`Rad etildi`) mavjud, lekin hech qayerda ishlatilmaydi (confirm/reject amali yo'q). Bu — "moderatsiya yo'q" kabi izchil topilma emas, balki enum mavjud-u ulanmagan holat — backend uni tabiiy ravishda to'ldiradi: xost `confirm`/`reject` qila oladi (to'lov/eskrov'siz, faqat status).
- **`client_id` majburiy.** Frontend so'rov formasi login talab qilmasa-da (`useCurrentUser()` bo'lsa ism/telefon oldindan to'ldiriladi, bo'lmasa ham forma ishlaydi ko'rinadi), backend'dagi barcha boshqa modullar `CurrentUser` talab qiladi — izchillik uchun bu yerda ham shunday.

## Ma'lumotlar modeli

`app/modules/tours/models.py`:

```python
class TourDifficulty(enum.StrEnum):
    Oson = "Oson"; Ortacha = "O'rtacha"; Qiyin = "Qiyin"; Ekstremal = "Ekstremal"

class TourBookingStatus(enum.StrEnum):
    pending = "pending"; confirmed = "confirmed"; rejected = "rejected"

class Tour(Base):
    __tablename__ = "tours"
    id: UUID (pk)
    operator_id: UUID (FK tour_operators.id, index)
    owner_id: UUID (FK users.id, index)          # operator.owner_id'dan nusxalanadi

    name: str(200)
    category: str | None (100)                    # 16 oldindan belgilangan toifadan biri (erkin matn)
    duration: str(100)                             # ko'rsatish matni, masalan "5 kun / 4 tun"
    nights: int | None                             # strukturaviy — filtrlash uchun
    region: Enum(Region, name="listing_region")    # listings.models.Region qayta ishlatiladi
    departure_city: str | None (100)
    meeting_point: str(500)
    difficulty: Enum(TourDifficulty, name="tour_difficulty") default=Ortacha
    group_size: str | None (100)

    price: Numeric(14,2)
    old_price: Numeric(14,2) default=0
    extra_fee: Numeric(14,2) default=0
    extra_fee_note: str | None (500)
    price_basis: str | None (200)

    airline: str | None (100)
    meal_plan: str | None (100)
    seats_left: int | None

    description: str(5000)
    cancellation_policy: str | None (1000)          # erkin matn (frontendga mos — strukturaviy siyosat emas)
    video_url: str | None (500)

    extra: dict (JSONB) default=dict                # itinerary, stops, includes, excludes, priceTiers, departures, faq

    pending: bool default=True
    rating: float default=0
    rating_count: int default=0
    created_at: DateTime server_default=func.now()

    photos: relationship("TourPhoto", cascade="all, delete-orphan")


class TourPhoto(Base):
    __tablename__ = "tour_photos"
    id: UUID (pk)
    tour_id: UUID (FK tours.id, ondelete=CASCADE, index)
    url: str(500); position: int default=0


class TourBooking(Base):
    __tablename__ = "tour_bookings"
    id: UUID (pk)
    tour_id: UUID (FK tours.id, index)
    client_id: UUID (FK users.id, index)
    name: str(150); phone: str(20)
    people: int
    total_estimate: Numeric(14,2)                   # serverda tour.price * people sifatida hisoblanadi
    status: Enum(TourBookingStatus, name="tour_booking_status") default=pending
    created_at: DateTime server_default=func.now()
```

**Muhim**: `region: Enum(Region, name="listing_region")` — `operators` modulida qo'llanilgan xuddi shu pattern: mavjud Postgres enum turi qayta ishlatiladi, migratsiyada `create_type=False` qo'lda qo'shiladi (avtogenerate'dan keyin tekshiriladi).

## Endpoints

Prefix `/api/v1`:

| Method | Path | Kim | Tavsif |
|---|---|---|---|
| GET | `/tours` | har kim | Qidiruv: `query, region, category, nights_min, nights_max, sort(rating\|newest\|price_asc\|price_desc), page, page_size`. Faqat `pending=False` turlar ko'rinadi |
| GET | `/tours/mine` | B2B | O'z turlari (pending bo'lsa ham ko'rinadi) |
| GET | `/tours/{id}` | har kim | `pending=True` bo'lsa — faqat egasi/ADMIN ko'ra oladi (Listings'dagi `_visible_to` patterni) |
| POST | `/tours` | B2B | Yaratadi — `operator_id` beriladi, backend operator egasi ekanini tekshiradi |
| PATCH | `/tours/{id}` | egasi/ADMIN | Tahrirlash |
| DELETE | `/tours/{id}` | egasi/ADMIN | O'chirish |
| POST | `/tours/{id}/photos` | egasi | Rasm yuklash (Listings/Operators pattern) |
| DELETE | `/tours/{id}/photos/{photo_id}` | egasi | Rasm o'chirish |
| POST | `/admin/tours/{id}/approve` | ADMIN | `pending: True → False` |
| POST | `/tours/{id}/bookings` | mijoz | So'rov yuboradi — `total_estimate` serverda hisoblanadi |
| GET | `/tours/{id}/bookings` | tur egasi | Shu turga tushgan so'rovlar |
| GET | `/tour-bookings/mine` | mijoz | O'zi yuborgan so'rovlar tarixi |
| POST | `/tour-bookings/{id}/confirm` | tur egasi | `pending → confirmed` |
| POST | `/tour-bookings/{id}/reject` | tur egasi | `pending → rejected` |

## Service funksiyalari

`app/modules/tours/service.py` — `listings/service.py` va yangi `operators/service.py` bilan bir xil pattern (`_get_or_404`, `_check_owner_or_admin`, `_visible_to`, `search`, `list_mine`, `create`, `update`, `delete`, `approve`, `add_photos`, `delete_photo`).

- `create()`: `operator_id` orqali `TourOperator`ni topadi, `operator.owner_id != current_user.id` bo'lsa `ForbiddenError` ("Faqat o'z operator profilingizga tur qo'sha olasiz"); `owner_id = operator.owner_id` nusxalanadi; `pending=True`.
- `search()`: faqat `pending=False`; `nights_min`/`nights_max` — `Tour.nights` ustida oraliq filtr (agar berilgan bo'lsa); `sort`: `rating.desc()` (standart) / `created_at.desc()` / `price.asc()` / `price.desc()`.

`app/modules/tours/booking_service.py` (yoki `service.py`ning bir qismi — implementatsiya vaqtida hal qilinadi, ehtimol bitta faylda qolsin, bookings moduli ham bitta `service.py`da edi):
- `create_booking(db, client, tour_id, name, phone, people)`: `total_estimate = tour.price * people`, `status=pending`.
- `confirm_booking`/`reject_booking(db, booking_id, host)`: faqat tur egasi (`tour.owner_id == host.id` yoki ADMIN), faqat `pending`dan o'tadi.

## Test strategiyasi

`tests/test_tours.py`:
1. Yaratish — faqat operator egasi yarata oladi (403 begona uchun); `pending=True` boshlanadi
2. Ommaviy qidiruv — `pending=True` turlar ko'rinmaydi; ADMIN approve qilgach ko'rinadi
3. `GET /tours/{id}` — pending holatda faqat egasi/ADMIN ko'radi, boshqa user 404
4. Qidiruv filtrlari — `region`, `nights_min/max`, `sort` variantlari
5. Tahrirlash/o'chirish — egalik tekshiruvi
6. Rasm yuklash/o'chirish
7. Tur bron so'rovi — yaratish (`total_estimate` to'g'ri hisoblanishi), egasi confirm/reject qiladi, begona user confirm qila olmaydi (403), noto'g'ri holatdan o'tish 409

## Migratsiya

`alembic revision --autogenerate -m "tours jadvali"`, `migrations/env.py`ga import qo'shiladi, `region` ustuni uchun `create_type=False` tekshiriladi (operators'dagi tajribaga ko'ra kerak bo'ladi).

## Doiradan tashqari (keyingi speclar)

- Reklama/aksiya to'lov oqimi (`TourActivation`) — Listings bilan birga alohida "promotion" spec
- Sharhlar (`reviews`, `faq` hozircha `extra`da statik)
- Real to'lov/eskrov tur bronlari uchun (agar kelajakda mahsulot talab qilsa)
- `rent_companies` moduli (navbatdagi)
