# Tour Operators moduli — dizayn

**Sana**: 2026-07-28
**Holat**: Taklif (foydalanuvchi tasdig'ini kutmoqda)

## Kontekst

Foydalanuvchi so'rovi bo'yicha ("Tours/Operators/RentCompanies") uchta yangi domen ustida ishlanadi. Bular birma-bir, alohida spec/plan/implement tsikli bilan quriladi (`listings`→`wallet`→`bookings` jarayoniga o'xshab): avval **Operators** (chunki `Tours` operatorga bog'liq, `RentCompanies` esa mustaqil), keyin `tours`, keyin `rent_companies`.

Bu spec yozishdan oldin frontend manbasi (`.../front/front2807/damber-front/`) uchta parallel tadqiqot orqali to'liq o'rganildi:
- `src/lib/types.ts` — `TourOperator` interfeysi (25+ maydon)
- `src/components/host/OperatorWizard.tsx` — yaratish/tahrirlash oqimi va validatsiya
- `src/store/myOperators.ts` — CRUD, moderatsiya yo'qligi
- `src/components/OperatorDetailView.tsx`, `src/app/operators/page.tsx`, `[id]/page.tsx` — ommaviy ko'rish/qidiruv

**Muhim topilma**: frontend'da `TourOperator` turi ikki xil profilni ifodalaydi — kompaniya (`kind: "operator"`) va yakka gid (`kind: "guide"`), bitta massivda. Bu spec **faqat kompaniya profillarini** qamrab oladi; gid profillari alohida, keyingi bosqichda qaraladi (frontend'ning o'zida ham `OperatorWizard`ning yuborilgan payload'ida `kind` yozilmasligi — bug — kuzatildi, shuning uchun buni backend'da ajratib olish tabiiy qaror).

## Loyihachi qarorlari (frontend'da yo'q yoki noaniq bo'lgan joylar)

- **Moderatsiya yo'q — frontend'ga mos.** `Listing`dan farqli o'laroq (`verified` maydoni, ADMIN tasdiqlashi bilan), frontend `TourOperator`da hech qanday status/moderatsiya maydoni yo'q — profil yaratilishi bilanoq ommaviy ko'rinadi. Bu spec ham shunga mos qoladi: operator profili yaratilgach darhol faol. Bu — Listings bilan asimmetriya, ammo frontend manbasini aynan takrorlash tamoyiliga ko'ra qasddan qilingan tanlov (kelajakda kerak bo'lsa moderatsiya alohida spec sifatida qo'shilishi mumkin).
- **`coords` — string emas, strukturaviy saqlanadi.** Frontend `coords: string` ("41.31° N, 69.27° E" yoki xom link yoki "—") sifatida saqlaydi. Backend buning o'rniga `lat: float | None`, `lng: float | None`, `location_link: str | None` saqlaydi — ko'rsatish uchun matn frontend/response darajasida hosil qilinadi. Bu ma'lumotni tozaroq saqlash, keyin xarita integratsiyasi uchun foydali (Listings'da ham lat/lng emas, faqat matn bor edi — bu yerda operator uchun kichik yaxshilash).
- **Rasm yuklash — Listings pattern'i qayta ishlatiladi.** Frontend'da `photos` massiv (data-URL yoki havola) sifatida saqlanadi va turga rasmiy tegishli emas (bolt-on). Backend'da Listings modulida allaqachon o'rnatilgan `ListingPhoto` + `StoragePort` + `add_photos`/`delete_photo` patterni operator uchun ham qayta qo'llaniladi (`TourOperatorPhoto` jadvali).
- **Video — faqat tashqi havola (`video_url`).** Frontend video faylni data-URL sifatida ham saqlay oladi (`videoFile`), lekin bu hech qayerda haqiqiy fayl-yuklash infratuzilmasidan (StoragePort) foydalanmaydi va murakkablik qo'shadi. V1'da faqat `video_url` (tashqi havola, masalan YouTube) qo'llab-quvvatlanadi; fayl yuklash keyingi bosqichga qoldiriladi.
- **Bitta userda bir nechta operator profili — ruxsat etiladi.** Frontend do'koni (`myOperators.ts`) buni texnik jihatdan cheklamaydi (faqat host dashboard UI eng oxirgisini ko'rsatadi); backend ham `owner_id` ustida noyoblik cheklovisiz qoladi — bu haqiqiy ma'lumotlar modeliga mos, sun'iy cheklov qo'shilmaydi.
- **Legacy `telegram`/`instagram`/`facebook` maydonlari qo'shilmaydi.** Frontend'da bular faqat eski profillar bilan moslik uchun saqlangan, yangi profillar faqat `social_links: list[str]` ishlatadi (`normalizeUrl()` orqali). Backend faqat `social_links`ni qo'llab-quvvatlaydi.

## Ma'lumotlar modeli

`app/modules/operators/models.py`:

```python
class OperatorSpecTag(enum.StrEnum):
    Tarixiy = "Tarixiy"
    Ekoturizm = "Ekoturizm"
    Xalqaro = "Xalqaro"
    HajUmra = "HajUmra"


SPEC_LABELS: dict[str, str] = {
    "Tarixiy": "Tarixiy va madaniy turlar",
    "Ekoturizm": "Ekoturizm va tog' trekkingi",
    "Xalqaro": "Xalqaro dam olish turlari",
    "HajUmra": "Haj va Umra safarlari",
}


class TourOperator(Base):
    __tablename__ = "tour_operators"

    id: UUID (pk)
    owner_id: UUID (FK users.id, index)

    name: str(200)
    tin: str(9)                              # STIR/INN — majburiy, 9 xonali
    license: str(255)
    license_doc_name: str | None (255)
    license_issued: str | None (255)          # serverda avtomatik: "{founded}-yil, ..."
    license_expiry: date | None

    founded: int                              # bo'lmasa joriy yil
    spec_tag: Enum(OperatorSpecTag) default=Tarixiy

    phone: str(20)
    email: str(255)
    website: str | None (255)
    office: str(500)
    region: Enum(Region)                      # listings.models.Region qayta ishlatiladi

    lat: float | None
    lng: float | None
    location_link: str | None (500)

    description: str(5000)
    social_links: list[str] (JSONB) default=[]
    video_url: str | None (500)

    rating: float default=0
    rating_count: int default=0

    created_at: datetime server_default=now

    photos: relationship → TourOperatorPhoto (cascade delete)


class TourOperatorPhoto(Base):
    __tablename__ = "tour_operator_photos"
    id: UUID (pk)
    operator_id: UUID (FK tour_operators.id, ondelete=CASCADE, index)
    url: str(500)
    position: int default=0
```

## Endpoints

Prefix `/api/v1`:

| Method | Path | Kim | Tavsif |
|---|---|---|---|
| GET | `/operators` | har kim | Ommaviy qidiruv: `query, region, spec_tag, sort(rating\|name\|newest), page, page_size` |
| GET | `/operators/mine` | B2B | Joriy foydalanuvchining o'z profillari (bir nechta bo'lishi mumkin) |
| GET | `/operators/{id}` | har kim | Bitta profil |
| POST | `/operators` | B2B | Yangi profil yaratadi |
| PATCH | `/operators/{id}` | egasi/ADMIN | Tahrirlash |
| DELETE | `/operators/{id}` | egasi/ADMIN | O'chirish (Tours moduli qo'shilganda `operator_id` FK `ON DELETE SET NULL` bo'lishi kerak — frontend'da "profil o'chsa, turlar saqlanadi") |
| POST | `/operators/{id}/photos` | egasi | Rasm yuklash (`listings`dagi bilan bir xil chekловlar: 10 tagacha, 5MB, jpg/png/webp) |
| DELETE | `/operators/{id}/photos/{photo_id}` | egasi | Rasm o'chirish |

## Service funksiyalari (`app/modules/operators/service.py`)

`listings/service.py`dagi bir xil pattern: `_get_or_404`, `_check_owner_or_admin`, `search`, `list_mine`, `create`, `update`, `delete`, `add_photos`, `delete_photo`.

- `create()`: `tin` 9-raqamli validatsiyasi schema darajasida (`Field(pattern=r"^\d{9}$")`); `license_issued` serverda `f"{founded}-yil, O'zbekiston Turizm va sport vazirligi tomonidan berilgan"` sifatida hosil qilinadi (frontend bilan bir xil matn); `founded` berilmasa `datetime.now().year`.
- `search()`: `query` — `name`/`description` bo'yicha `ILIKE`; `region`/`spec_tag` — aniq moslik; `sort` — `rating.desc()` (standart) / `name.asc()` / `created_at.desc()`.

## Validatsiya (`schemas.py`)

`OperatorCreateRequest` majburiy maydonlar (`OperatorWizard.validate()`dan port): `name`, `tin` (9 raqam), `license`, `license_expiry`, `office`, `phone`, `email`, `description`. Qolganlari ixtiyoriy.

## Test strategiyasi

`tests/test_operators.py`:
1. Yaratish — muvaffaqiyatli, `license_issued` avtomatik hosil bo'lishi, `founded` standart qiymati
2. Yaratish — `tin` noto'g'ri formatda → 422
3. Ommaviy qidiruv — `region`/`spec_tag`/`query` filtrlari, `sort` variantlari
4. Egalik — begona user tahrirlay/o'chira olmaydi (403)
5. Bir userda bir nechta profil yaratish mumkinligini tekshirish
6. Rasm yuklash/o'chirish (listings testlariga o'xshash)

## Migratsiya

`alembic revision --autogenerate -m "tour_operators jadvali"`, oldindan `migrations/env.py`ga `app.modules.operators.models` importi qo'shiladi.

## Doiradan tashqari (keyingi speclar)

- Gid (`kind: "guide"`) profillari — alohida modul/spec
- Moderatsiya/tasdiqlash workflow'i (agar kelajakda kerak bo'lsa)
- Video fayl yuklash (hozircha faqat `video_url`)
- `tours` moduli (operatorga bog'langan turlar, shu FK orqali)
