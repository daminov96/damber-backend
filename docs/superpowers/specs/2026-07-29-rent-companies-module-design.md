# Rent Companies moduli — dizayn

**Sana**: 2026-07-29
**Holat**: Taklif (foydalanuvchi tasdig'ini kutmoqda)

## Kontekst

`operators` → `tours`dan keyingi bosqich, ketma-ketlikdagi oxirgi modul (`listings`→`wallet`→`bookings`→`operators`→`tours`→**`rent_companies`**). Frontend tadqiqoti oldingi sessiyada allaqachon qilingan: `src/lib/types.ts` (`RentCompany` interfeysi), `src/lib/rentcar.ts`, `src/components/host/RentCompanyWizard.tsx`, `src/store/myRentCompanies.ts`, `src/components/host/HostRentTab.tsx`.

**Asosiy topilma**: `RentCompany` — mustaqil biznes mantig'i deyarli yo'q, yengil profil-wrapper. Hech qanday status/moderatsiya maydoni yo'q (Operators kabi). Haqiqiy ijara biznes qoidalari (narx, depozit, kilometraj, haydovchi talablari) individual `RentCar` turidagi `Listing`larda yashaydi (`typeExtras` orqali), kompaniyada emas. `RentCar` bronlari mavjud `bookings` oqimidan **hech qanday farqi yo'q** — grep bilan tasdiqlandi, `refund.ts`/`GatewaySim.tsx`da RentCar alohida ko'rib chiqilmaydi.

**Bog'lanish mexanizmi**: `Listing.companyId?: string` — frontend'da xost o'ziga tegishli `RentCompany` profili bo'lsa, **har doim avtomatik** shu profilga bog'lanadi (host tanlagan "Kompaniya orqali/Shaxsiy" radio tugmasidan qat'iy nazar — bu prototipdagi ehtimoliy xato, tadqiqotda alohida qayd etilgan).

## Ushbu sessiyada topilgan qo'shimcha muammo (Operators/Tours)

Kod ko'rib chiqilganda aniqlandi: `Tour.operator_id` FK'si hech qanday `ondelete` siyosatisiz (Postgres standart holati — `RESTRICT`), lekin `operators/service.py::delete()` bu holatni oldindan tekshirmaydi. Natijada: turlari mavjud operator profilini o'chirishga urinilsa, tuzatilmagan Postgres `IntegrityError` sifatida **500** xatosi foydalanuvchiga chiqadi — buzilgan xatolik boshqaruvi. Bu **shu spec doirasida tuzatiladi** (`operators/service.py::delete()`ga oldindan tekshiruv qo'shiladi, `ConflictError` 409 bilan), chunki xuddi shu FK-o'chirish muammosi `RentCompany`→`Listing` bog'lanishida ham paydo bo'ladi va ikkalasini bir xil, izchil tamoyil bilan hal qilish to'g'ri.

## Loyihachi qarorlari

- **Moderatsiya yo'q — Operators bilan izchil.** Frontendda status maydoni yo'q, profil yaratilishi bilan faol.
- **`company_id` — `RESTRICT` emas, `ON DELETE SET NULL`.** `Listing.company_id` ixtiyoriy (nullable) — mashina kompaniyasiz ham mavjud bo'la oladi (frontend `companyId?`ning o'zi ixtiyoriy). Shuning uchun kompaniya o'chirilganda uning mashinalari **o'chirilmaydi, faqat bog'lanish uziladi** (`company_id = NULL`) — frontend xatti-harakatiga yaqinroq ("kompaniya o'chsa, mashinalar saqlanadi", Operators/Tours'dagi "operator o'chsa, turlar saqlanadi" bilan bir xil mantiq, lekin bu yerda DB darajasida avtomatik bajariladi, chunki bog'lanish ixtiyoriy).
- **`company_id` biriktirish — AVTOMATIK emas, EXPLICIT.** Frontenddagi "har doim avtomatik biriktirish" xatti-harakati **qasddan takrorlanmaydi** — bu tadqiqotda aniq xato/nomuvofiqlik sifatida qayd etilgan (xost "Shaxsiy" tanlasa ham kompaniyaga bog'lanadi). Backend'da `company_id` — `ListingCreateRequest`/`UpdateRequest`dagi oddiy ixtiyoriy maydon: xost aniq ko'rsatishi kerak, backend faqat (a) shu kompaniya joriy foydalanuvchiga tegishli ekanini va (b) `type == RentCar` ekanini tekshiradi. Bu — prototipdagi tasodifiy nuqsonni emas, mahsulot niyatini ("xost tanlab bog'laydi") to'g'ri amalga oshirish.
- **Bitta userda bir nechta kompaniya — ruxsat etiladi.** Operators'dagi bir xil qaror: frontend do'koni texnik jihatdan cheklamaydi (faqat host dashboard UI birinchisini ko'rsatadi), backend sun'iy cheklov qo'ymaydi.
- **Ommaviy ko'rish endpoint'lari qo'shiladi — frontendda yo'q, lekin qasddan emas.** Tadqiqot frontendda `RentCompany` uchun alohida ommaviy sahifa yo'qligini tasdiqladi (Operators'dan farqli). Bu — mahsulot qarori emas, tugallanmagan UI (`companyId` yoziladi-yu hech qayerda o'qilmaydi). Backend izchillik uchun (Operators/Listings bilan bir xil pattern) baribir `GET /rent-companies`, `GET /rent-companies/{id}` qo'shadi — frontend keyinchalik shu API'dan foydalanishi mumkin.
- **Litsenziya fayli — faqat nom (string), StoragePort orqali haqiqiy yuklash yo'q.** `RentCompanyWizard`da litsenziya fayli **majburiy** (Operators'dan farqli — u yerda ixtiyoriy edi), shuning uchun `license_doc_name: str` (majburiy, `license_doc_name: str | None` emas). Haqiqiy fayl-yuklash (StoragePort) faqat rasm (`photos`) uchun qo'llaniladi — Operators/Listings bilan bir xil.
- **`logo` — oddiy URL maydoni.** Operators'dagi `video_url` kabi — StoragePort integratsiyasisiz, faqat matn maydoni.

## Ma'lumotlar modeli

`app/modules/rent_companies/models.py`:

```python
class RentCompany(Base):
    __tablename__ = "rent_companies"
    id: UUID (pk)
    owner_id: UUID (FK users.id, index)

    name: str(200)
    tin: str(9)
    license: str(255)
    license_doc_name: str(255)                     # majburiy (wizard: fayl yuklash shart)
    founded: int

    phone: str(20)
    phone2: str | None (20)
    email: str(255)
    website: str | None (255)
    office: str(500)
    district: str | None (100)
    region: Enum(Region, name="listing_region")     # operators/tours'dagi kabi qayta ishlatiladi

    lat: float | None; lng: float | None; location_link: str | None (500)

    description: str(5000)
    work_hours: str | None (100)                     # "24/7" yoki "08:00 - 22:00"
    pickup_zones: list[str] (JSONB) default=list      # kamida 1 ta (schema darajasida)
    payment_methods: list[str] (JSONB) default=list   # kamida 1 ta (schema darajasida)
    social_links: list[str] (JSONB) default=list

    bank_name: str | None (255)
    bank_account: str | None (50)
    bank_mfo: str | None (20)

    logo: str | None (500)

    rating: float default=0; rating_count: int default=0
    created_at: DateTime server_default=func.now()

    photos: relationship("RentCompanyPhoto", cascade="all, delete-orphan")


class RentCompanyPhoto(Base):
    __tablename__ = "rent_company_photos"
    id: UUID (pk)
    company_id: UUID (FK rent_companies.id, ondelete="CASCADE", index)
    url: str(500); position: int default=0
```

`app/modules/listings/models.py`ga qo'shimcha (mavjud `Listing` klassiga):

```python
company_id: Mapped[uuid.UUID | None] = mapped_column(
    ForeignKey("rent_companies.id", ondelete="SET NULL"), nullable=True, index=True
)
```

## Endpoints

Prefix `/api/v1`:

| Method | Path | Kim | Tavsif |
|---|---|---|---|
| GET | `/rent-companies` | har kim | `query, region, sort(rating\|name\|newest), page, page_size` |
| GET | `/rent-companies/mine` | B2B | O'z profillari (bir nechta bo'lishi mumkin) |
| GET | `/rent-companies/{id}` | har kim | Bitta profil |
| POST | `/rent-companies` | B2B | Yaratadi (`pickup_zones`/`payment_methods` kamida 1 ta) |
| PATCH | `/rent-companies/{id}` | egasi/ADMIN | Tahrirlash |
| DELETE | `/rent-companies/{id}` | egasi/ADMIN | O'chirish — bog'liq listinglar `company_id=NULL` bo'ladi (DB `ON DELETE SET NULL`, qo'shimcha app-darajasida tekshiruv shart emas) |
| POST | `/rent-companies/{id}/photos` | egasi | Rasm yuklash |
| DELETE | `/rent-companies/{id}/photos/{photo_id}` | egasi | Rasm o'chirish |
| GET | `/rent-companies/{id}/listings` | har kim | Shu kompaniyaga bog'langan (`company_id`) tasdiqlangan listinglar ro'yxati |

`listings` moduliga o'zgartirish: `ListingCreateRequest`/`ListingUpdateRequest`ga `company_id: uuid.UUID | None = None` qo'shiladi; `listings/service.py::create`/`update`da validatsiya — `company_id` berilgan bo'lsa: (a) shunday `RentCompany` mavjudligi, (b) uning `owner_id == current_user.id` ekanligi (`ForbiddenError` aks holda), (c) `type == RentCar` ekanligi (`HTTPException(400, "company_id faqat RentCar turidagi e'lonlarga biriktiriladi")`).

## Service funksiyalari

`app/modules/rent_companies/service.py` — `operators/service.py`dagi bir xil pattern (`_get_or_404`, `_check_owner_or_admin`, `search`, `list_mine`, `create`, `update`, `delete`, `add_photos`, `delete_photo`) + `list_listings(db, company_id, page, page_size)` — `Listing.company_id == company_id AND Listing.verified.is_(True) AND Listing.paused.is_(False)` (faqat ommaviy ko'rinadigan listinglar, Listings'dagi `search()` filtri bilan bir xil).

`app/modules/operators/service.py::delete()`ga tuzatish:

```python
async def delete(db: AsyncSession, operator_id: uuid.UUID, current_user: User) -> None:
    operator = await _get_or_404(db, operator_id)
    _check_owner_or_admin(operator, current_user)
    has_tours = await db.execute(select(Tour.id).where(Tour.operator_id == operator_id).limit(1))
    if has_tours.first():
        raise ConflictError("Bu operatorga tegishli turlar mavjud — avval ularni o'chiring")
    await db.delete(operator)
    await db.commit()
```

(`Tour` — `app.modules.tours.models`dan import qilinadi; aylanma import yo'q, chunki `tours.models` `operators.models`ga bog'liq emas — faqat `tours.service` bog'liq.)

## Validatsiya

`RentCompanyCreateRequest`: `name`, `tin` (9 raqam), `license`, `license_doc_name` (majburiy), `office`, `phone`, `email`, `description` majburiy; `pickup_zones: list[str] = Field(min_length=1)`, `payment_methods: list[str] = Field(min_length=1)` — Pydantic v2'da ro'yxat uzunligi to'g'ridan-to'g'ri `Field(min_length=1)` bilan tekshiriladi (`RentCompanyWizard.validate()`dagi "kamida 1 ta" qoidasi).

## Test strategiyasi

`tests/test_rent_companies.py`:
1. Yaratish — muvaffaqiyatli; `pickup_zones`/`payment_methods` bo'sh bo'lsa 422
2. Darhol ko'rinish — moderatsiyasiz (Operators'dagi bilan bir xil test)
3. Qidiruv/saralash
4. Egalik — tahrirlash/o'chirish
5. Ko'p profil — bitta user bir nechta kompaniya yarata olishi
6. Rasm yuklash/o'chirish
7. **Listing bog'lanishi**: `company_id` bilan `RentCar` listing yaratish muvaffaqiyatli; begona userning kompaniyasiga bog'lashga urinish 403; `type != RentCar`da `company_id` berish 400
8. **Kaskad**: kompaniya o'chirilganda unga bog'langan listingning `company_id`si `None` bo'lib qolishi (o'chirilmasligi)
9. `GET /rent-companies/{id}/listings` — faqat tasdiqlangan/faol listinglar ko'rinishi

`tests/test_operators.py`ga qo'shimcha:
10. Turlari mavjud operatorni o'chirishga urinish — 409 (yangi tuzatishni tekshiradi)

## Migratsiya

Ikkita migratsiya bosqichi bitta faylda (yoki ikkita ketma-ket): `rent_companies`/`rent_company_photos` jadvallari yaratiladi, so'ng `listings.company_id` ustuni `ALTER TABLE` bilan qo'shiladi (FK `rent_companies.id`ga, `ondelete=SET NULL`). `region` ustuni uchun operators/tours'dagi tajribaga ko'ra `create_type=False` kerak bo'ladi.

## Doiradan tashqari

- Litsenziya faylini haqiqiy yuklash (StoragePort) — hozircha faqat nom
- Kompaniya darajasidagi analitika/statistika
- Xarita integratsiyasi (`pickup_zones` hozircha erkin matn ro'yxati)
