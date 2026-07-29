# Guides moduli — dizayn

**Sana**: 2026-07-29
**Holat**: Taklif (foydalanuvchi tasdig'ini kutmoqda)

## Kontekst

`operators`/`tours`/`rent_companies`dan keyingi bosqich — foydalanuvchi bilan kelishilgan: barcha backend modullari to'liq tugagach frontend API'ga ulanadi, hozircha davom etamiz. `operators` spec'ida "Gid profillari — alohida modul/spec"ga qoldirilgan edi; bu spec o'sha bo'shliqni to'ldiradi.

Frontend tadqiqoti (yangi, ushbu sessiyada) — `GuideWizard.tsx`, `GuideActivation.tsx`, `store/guideActivation.ts`, `OperatorDetailView.tsx`dagi `isGuide` shoxobchasi, `HostToursTab.tsx`.

**Asosiy topilma**: frontend'da Gid — `TourOperator` turining `kind: "guide"` varianti, **bir xil jadval/massivda** kompaniyalar bilan birga saqlanadi (`useMyOperators`), chunki "katalog, profil sahifasi va tur bog'lash mantig'i bir xil bo'lib qolishi" uchun shunday qilingan (frontend'ning o'z izohi). Ammo **maydonlar deyarli butunlay boshqacha** — Gidda F.I.SH./avatar/tillar/tajriba/soatbay-kunlik narx/mashina bor, Operatorda kompaniya nomi/litsenziya/ofis/tashkil topgan yil bor — **umumiy maydon deyarli yo'q** (faqat telefon/email/postedDate).

## Loyihachi qaror: alohida `guides` jadvali (operators bilan bitta jadvalda emas)

Bu — ushbu spec'dagi eng muhim arxitektura qarori, shuning uchun asoslab o'tiladi:

Frontend ikkalasini bitta massivda saqlaydi, lekin bu **domen talabi emas — implementatsiya qulayligi** (kod izohida aniq aytilgan). Agar backend'da ham shunday qilinsa, natija — deyarli barcha ustunlari NULL bo'ladigan "God table": Operator yozuvida gidga xos 15 ta ustun har doim NULL, Gid yozuvida kompaniyaga xos 8 ta ustun har doim NULL. Bu — junior xato sifatida tanilgan naqsh (sparse table / kind-discriminator antipattern). Ikkala tur o'rtasida real overlap deyarli yo'qligi buni yanada asoslaydi (Listings'dagi `ListingType`lar esa aksincha — barchasi umumiy `weekday_price`/`capacity`/`amenities` ustunlariga ega, shuning uchun bitta jadvalda `type` enum bilan saqlash u yerda to'g'ri edi; bu yerda vaziyat butunlay boshqacha).

**Natija**: `guides` — mustaqil jadval, mustaqil model, mustaqil CRUD moduli — `operators`ga o'xshab (moderatsiyasiz, shu naqsh), lekin butunlay boshqa maydonlar to'plami bilan.

## Tours bilan bog'lanish — muhim o'zgarish

Frontend'da `Tour.operatorId` — gid ham, kompaniya ham shu bitta maydonga bog'lanadi (turi farqlanmaydi). Backend'da alohida jadval tanlangani sabab, bu endi ishlamaydi. Yechim: **`Tour.operator_id` ixtiyoriy bo'ladi, yangi `Tour.guide_id` (ixtiyoriy) qo'shiladi, va DB darajasida CHECK constraint — ikkalasidan aynan bittasi to'ldirilgan bo'lishi shart** (polimorfik-egalik naqshi, "aynan bittasi" invariantini ilova kodiga emas, DBga ishonib topshirish — senior arxitektura amaliyoti).

```sql
CHECK (
  (operator_id IS NOT NULL AND guide_id IS NULL) OR
  (operator_id IS NULL AND guide_id IS NOT NULL)
)
```

## Moderatsiya — Operators bilan bir xil qaror (yo'q)

Frontend'dagi "Moderatsiya" bosqichi (`GuideActivation`) — sof vizual animatsiya, `addOperator()` chaqirilganda profil darhol jonli massivga qo'shiladi, hech qanday `pending`/status maydoni yo'q. Bu — Operators'da qabul qilingan qaror bilan **aynan bir xil holat** (frontendda status maydoni yo'q → backend ham qo'ymaydi).

## `certified` — mijozga ishonilmaydi, serverda hisoblanadi

Frontend: `certified: !!f.licenseFileName` — foydalanuvchi istalgan faylni tanlashi bilan (hatto haqiqiy sertifikat bo'lmasa ham) `true` bo'lib qoladi, hech qanday real tekshiruv yo'q. Backend bu **aynan shu biznes qoidasini** takrorlaydi (frontendga mos — soxta "haqiqiy verifikatsiya" o'ylab topilmaydi), lekin **mijozdan `certified` maydoni qabul qilinmaydi** — server `license_doc_name is not None` asosida o'zi hisoblaydi (`create`/`update`da). Bu kichik, lekin muhim farq: frontend mijoz-tomonda hisoblaydi (ishonchli emas), backend server-tomonda hisoblaydi (soxtalashtirib bo'lmaydi — garchi haligacha "haqiqiy" tekshiruv bo'lmasa-da).

## Reklama/promo to'lov oqimi — doiradan tashqari

`GuideActivation`dagi to'lov bosqichi (`wallet.pay()` orqali) — Listings/Tours uchun ham hali qurilmagan xuddi shu funksiya. Izchillik uchun bu yerda ham qurilmaydi.

## Ma'lumotlar modeli

`app/modules/guides/models.py`:

```python
class GuideType(enum.StrEnum):
    Individual = "Individual gid"
    Ekskursovod = "Ekskursovod / Hamroh"
    TogGidi = "Tog' gidi / Ekogid"
    GidHaydovchi = "Gid-haydovchi"

class GuideEmployment(enum.StrEnum):
    Mustaqil = "Mustaqil (yakka tartibdagi) gid"
    Turagentlik = "Turagentlik / turoperator xodimi"
    Muzey = "Muzey yoki qo'riqxona xodimi"

class Guide(Base):
    __tablename__ = "guides"
    id: UUID (pk)
    owner_id: UUID (FK users.id, index)

    name: str(200)                                   # F.I.SH.
    avatar: str | None (500)
    guide_type: Enum(GuideType) default=Individual
    employment: Enum(GuideEmployment) default=Mustaqil

    license: str | None (255)                         # sertifikat raqami — ixtiyoriy (frontend "—" bilan
                                                        # to'ldiradi, backend shunchaki NULL qoldiradi)
    license_expiry: date | None
    license_doc_name: str | None (255)                 # faqat fayl nomi — haqiqiy yuklash yo'q (Operators'dagi kabi)
    certified: bool default=False                       # SERVERDA hisoblanadi, mijoz yubormaydi

    tin: str | None (9)                                 # ixtiyoriy — Operators/RentCompanies'dan farqli

    languages: list[str] (JSONB) default=list           # kamida 1 ta (schema)
    experience_years: int | None
    region: Enum(Region, name="listing_region")          # qayta ishlatiladi
    office: str | None (500)                             # uchrashuv joyi

    service_areas: list[str] (JSONB) default=list        # kamida 1 ta
    specialties: list[str] (JSONB) default=list          # kamida 1 ta

    hourly_price: Numeric(14,2) | None
    daily_price: Numeric(14,2) | None                    # ikkisidan kamida bittasi (schema)
    price_includes: list[str] (JSONB) default=["Gidlik xizmati"]
    max_group_size: str | None (100)                     # erkin matn — to'liq katalog aniqlanmagan
    cancellation_policy: str | None (500)                # erkin matn — to'liq katalog aniqlanmagan

    has_car: bool default=False
    car_model: str | None (100)                          # has_car=True bo'lsa majburiy (schema)
    car_seats: int | None

    phone: str(20); email: str(255)
    social_links: list[str] (JSONB) default=list
    video_url: str | None (500)

    description: str(2000)                                # kamida 20 belgi (schema)

    rating: float default=0; rating_count: int default=0
    created_at: DateTime server_default=func.now()

    photos: relationship("GuidePhoto", cascade="all, delete-orphan")


class GuidePhoto(Base):
    __tablename__ = "guide_photos"
    id: UUID (pk)
    guide_id: UUID (FK guides.id, ondelete="CASCADE", index)
    url: str(500); position: int default=0
```

`app/modules/tours/models.py`ga o'zgartirish:
```python
operator_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tour_operators.id"), nullable=True, index=True)
guide_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("guides.id"), nullable=True, index=True)
# __table_args__ ga CHECK constraint qo'shiladi (yuqoridagi SQL)
```

## Endpoints

Prefix `/api/v1` (Operators bilan bir xil tuzilma):

| Method | Path | Kim | Tavsif |
|---|---|---|---|
| GET | `/guides` | har kim | `query, region, guide_type, sort(rating\|name\|newest), page, page_size` |
| GET | `/guides/mine` | B2B | O'z profillari |
| GET | `/guides/{id}` | har kim | Bitta profil |
| POST | `/guides` | B2B | Yaratadi — `certified` serverda hisoblanadi |
| PATCH | `/guides/{id}` | egasi/ADMIN | Tahrirlash — `certified` qayta hisoblanadi |
| DELETE | `/guides/{id}` | egasi/ADMIN | O'chirish — bog'liq turlar bo'lsa 409 (Operators'dagi tuzatilgan pattern) |
| POST | `/guides/{id}/photos` | egasi | Rasm yuklash |
| DELETE | `/guides/{id}/photos/{photo_id}` | egasi | Rasm o'chirish |

`tours` moduliga o'zgartirish:
- `TourCreateRequest`: `operator_id: uuid.UUID | None = None`, `guide_id: uuid.UUID | None = None` — `model_validator(mode="after")` bilan "aynan bittasi to'ldirilgan" tekshiruvi (422, DB CHECK'dan oldin, foydalanuvchiga tushunarli xato uchun).
- `tours/service.py::create()`: `operator_id` yoki `guide_id`dan qay biri berilgan bo'lsa, shunga mos egalikni tekshiradi (`operator.owner_id`/`guide.owner_id == current_user.id`), `owner_id` shundan nusxalanadi.
- `TourOut`ga `guide_id: uuid.UUID | None` qo'shiladi.

## Service funksiyalari

`app/modules/guides/service.py` — `operators/service.py`dagi bir xil pattern (`_get_or_404`, `_check_owner_or_admin`, `search`, `list_mine`, `add_photos`, `delete_photo`), farqlar:
- `create()`/`update()`: `certified = payload.license_doc_name is not None` — har doim serverda qayta hisoblanadi, `CreateRequest`/`UpdateRequest`da `certified` maydoni umuman yo'q (mijoz yubora olmaydi).
- `delete()`: Operators'dagi tuzatilgan pattern — bog'liq `Tour`lar bo'lsa (`Tour.guide_id == guide_id`) `ConflictError` 409.

`tours/service.py`ga o'zgartirish — `_get_operator`/`_get_guide` ikkalasi ham bo'lishi, `create()` qay biri berilganiga qarab tanlaydi.

## Validatsiya (`guides/schemas.py`)

`GuideCreateRequest` majburiy: `name` (min 2 so'z — `model_validator`), `languages` (min_length=1), `service_areas` (min_length=1), `specialties` (min_length=1), `phone`, `email`, `description` (min_length=20). `hourly_price`/`daily_price`dan kamida bittasi berilishi shart (`model_validator`). `has_car=True` bo'lsa `car_model` majburiy (`model_validator`). `tin` berilsa 9-raqamli.

## Test strategiyasi

`tests/test_guides.py` (`test_operators.py` uslubi):
1. Yaratish — muvaffaqiyatli; `license_doc_name` berilsa `certified=True` bo'lishi (mijoz `certified=true` yuborsa e'tiborsiz qoldirilishi/qabul qilinmasligi)
2. Validatsiya — `languages`/`service_areas`/`specialties` bo'sh → 422; ikkala narx ham yo'q → 422; `has_car=True` lekin `car_model` yo'q → 422
3. Darhol ko'rinish (moderatsiyasiz)
4. Qidiruv/saralash
5. Egalik — tahrirlash/o'chirish
6. Turlari mavjud gidni o'chirish → 409
7. Rasm yuklash/o'chirish
8. **Tours integratsiyasi**: `guide_id` bilan tur yaratish muvaffaqiyatli, `owner_id` gid egasidan nusxalanishi; `operator_id` VA `guide_id` ikkalasi ham berilsa 422; ikkalasi ham berilmasa 422; begona gidga bog'lashga urinish 403

`tests/test_tours.py`ga tuzatish: mavjud testlar `operator_id`ni ishlatishda davom etadi (backward-compatible — `operator_id` hali ham qo'llab-quvvatlanadi, faqat endi ixtiyoriy ikkitadan biri).

## Migratsiya

`alembic revision --autogenerate -m "guides jadvali va tours guide_id"`. `Tour.operator_id`ni nullable qilish autogenerate tomonidan `ALTER COLUMN ... DROP NOT NULL` sifatida aniqlanadi. CHECK constraint autogenerate tomonidan aniqlanmaydi — **qo'lda** `op.create_check_constraint(...)` qo'shiladi. `region` uchun odatdagidek `create_type=False`.

## Doiradan tashqari

- Haqiqiy sertifikat verifikatsiyasi (hozircha faqat fayl nomi + o'z-o'zidan e'lon qilingan bayroq)
- Reklama/promo to'lov oqimi
- `max_group_size`/`cancellation_policy` uchun qat'iy enum (to'liq katalog frontend kodida aniqlanmagan)
