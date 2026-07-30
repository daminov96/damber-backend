# Plans moduli — dizayn

**Sana**: 2026-07-30
**Holat**: Taklif (foydalanuvchi tasdig'ini kutmoqda)

## Kontekst

`reviews`dan keyingi bosqich. `User.current_plan_id` ustuni allaqachon mavjud (B2B ro'yxatdan o'tishda `"free"` qo'yiladi), lekin hech qanday Plans moduli yo'q.

Frontend tadqiqoti (ikki bosqichda — birinchi urinish server xatosi bilan uzilib qoldi, ikkinchi marta to'liq bajarildi) shuni tasdiqladi:

- **4 ta qat'iy tarif**: `free` (0 so'm, standart), `standard` (150,000), `business` (300,000, "Tavsiya etamiz"), `premium` (450,000, "👑"). Har biri `photoLimit`/`videoLimit`/`videoSizeMb` va marketing matni (`features[]`) bilan.
- **Yillik narx** — saqlanadigan maydon emas, `Math.round(oylik*12*0.84)` — sof hisoblash funksiyasi.
- **Hech qanday muddat/yangilanish yo'q** — "30 kun amal qiladi" degan matn faqat marketing matni, hech qayerda amalga oshirilmagan (`planExpiry`/`renewalDate`/`billingCycle` saqlash maydoni umuman yo'q).
- **Hech qanday cheklov haqiqatda kuchga kiritilmagan** — `photoLimit`/`videoLimit`/e'lonlar soni chegarasi hech qayerda tekshirilmaydi (rasm yuklashda, tur/listing yaratishda). Bu — `certified`/`rating` kabi "ko'ринishda jonli, aslida statik" holat, lekin ulardan ham kuchliroq: hatto UI darajasida ham hech qanday urinish yo'q (Review'dagi "Baholash" tugmasi gating'idan farqli — bu yerda hech qanday niyat izi ham yo'q).
- **Plans va Promotion (reklama paketi) — ikki mutlaqo alohida tizim.** `data/promo.ts` (`PromoPackage`/`PromoAddon`, `free/starter/fast/premium` id maydoni) — bu alohida, listing/tur/gid darajasida (`Listing.promo`), Plans bilan hech qanday kod bog'lanishisiz. Bu spec Plans (hisob darajasidagi tarif)ni qamrab oladi; Promotion oldingi specларда ("doiradan tashqari") qoldirilganidek qoladi.
- `setPlan()` faqat `user.currentPlanId`ni o'zgartiradi; wallet to'lovi alohida, chaqiruvchi tomonda (`HostPlansTab.tsx`) amalga oshiriladi.

## Loyihachi qarorlar

- **Tarif katalogi — DB jadvali emas, kod darajasidagi statik katalog.** Frontendda `plans.ts` — 4 ta qat'iy, kod darajasida belgilangan yozuv (CMS/admin tahrirlash imkoniyati yo'q). Bu Bookings modulidagi `PROMO_CODES` konstantasi bilan bir xil naqsh — kichik, o'zgarmas biznes katalogi uchun DB jadvali ortiqcha murakkablik qo'shardi (YAGNI). `app/modules/plans/catalog.py`da Python lug'ati sifatida saqlanadi.
- **Cheklovlar (photo_limit/video_limit) — kuchga kiritilmaydi.** Frontendda hech qanday shaklda (hatto UI darajasida ham) amalga oshirilmagan haqiqiy mahsulot bo'shlig'i — bu Review'dagi bron-gating holatidan farqli ("aniq niyat, amalga oshirilmagan"), bu yerda **hech qanday niyat izi yo'q**. Shuning uchun bu spec **o'ylab topilgan** cheklov mantig'ini qo'shmaydi — faqat katalog ma'lumotini API orqali chiqaradi (kelajakda kerak bo'lsa alohida spec sifatida qo'shiladi).
- **Tarif tarixi (`PlanPurchase`) — qo'shiladi, frontendda yo'q.** Frontendda tarif sotib olish faqat umumiy `WalletTx` yozuviga (`kind: "promo"`) yashiringan — alohida audit yozuvi yo'q. Bu haqiqiy backend uchun yetarli emas (moliyaviy operatsiya — kim, qachon, qaysi tarifni, qancha to'lab sotib olgani kuzatilishi kerak). Shuning uchun `PlanPurchase` jadvali qo'shiladi — bu yangi mahsulot xususiyati emas, moliyaviy operatsiyani to'g'ri yozib borish (har bir CRUD modulida qilingani kabi audit maydonlari qo'shish bilan bir xil daraja).
- **`WalletTxKind`ga `plan` qiymati qo'shiladi.** Hozir `topup/promo/booking/refund/other` bor; frontend tarif sotib olishni umumiy `"promo"` sifatida belgilaydi — bu Promotion (reklama paketi) bilan chalkashtiradi. Backend aniqroq: alohida `plan` turi.
- **Muddat/yangilanish — qo'shilmaydi.** Frontendda umuman yo'q, backend ham qo'shmaydi (muddatsiz cheklov ma'nosiz bo'lardi — yuqoridagi qarorga mos).
- **Faqat B2B.** `current_plan_id` tushunchasi B2B'ga xos (frontendda faqat B2B ro'yxatdan o'tishda o'rnatiladi).
- **Bir xil tarifga "qayta sotib olish" — bloklanadi.** Frontend tugmasi `isCurrent`da o'chirilgan — backend buni haqiqiy 409 bilan ta'minlaydi.

## Ma'lumotlar modeli

`app/modules/plans/catalog.py` (DB emas, kod darajasida):

```python
class PlanId(enum.StrEnum):
    free = "free"
    standard = "standard"
    business = "business"
    premium = "premium"

@dataclass(frozen=True)
class PlanDefinition:
    id: PlanId
    name: str
    price: float
    photo_limit: int
    video_limit: int
    video_size_mb: int
    badge: str | None
    emblem: str | None
    features: list[str]

PLAN_CATALOG: dict[PlanId, PlanDefinition] = {
    PlanId.free: PlanDefinition(PlanId.free, "Bepul", 0, 10, 0, 0, None, None, [...]),
    PlanId.standard: PlanDefinition(PlanId.standard, "Standart", 150_000, 20, 1, 30, None, None, [...]),
    PlanId.business: PlanDefinition(PlanId.business, "Biznes", 300_000, 30, 2, 50, "Tavsiya etamiz", "TOP", [...]),
    PlanId.premium: PlanDefinition(PlanId.premium, "Premium VIP", 450_000, 50, 3, 100, None, "👑", [...]),
}

def yearly_price(monthly_price: float) -> float:
    return round(monthly_price * 12 * 0.84)
```

`app/modules/plans/models.py`:

```python
class BillingCycle(enum.StrEnum):
    monthly = "monthly"
    yearly = "yearly"

class PlanPurchase(Base):
    __tablename__ = "plan_purchases"
    id: UUID (pk)
    user_id: UUID (FK users.id, index)
    plan_id: Enum(PlanId, name="plan_id")
    billing_cycle: Enum(BillingCycle, name="plan_billing_cycle")
    price_paid: Numeric(14,2)
    created_at: DateTime server_default=func.now()
```

`app/modules/wallet/models.py`ga qo'shimcha: `WalletTxKind.plan = "plan"` (mavjud enumga bitta qiymat — Postgres `ALTER TYPE wallet_tx_kind ADD VALUE 'plan'`, alembic buni avtomatik yozadi).

## Endpoints

Prefix `/api/v1`:

| Method | Path | Kim | Tavsif |
|---|---|---|---|
| GET | `/plans` | ochiq | To'liq katalog — har bir tarif uchun `price` (oylik) va `yearly_price` (hisoblangan) |
| GET | `/plans/mine` | B2B | Joriy tarif ma'lumoti (`current_plan_id` + to'liq `PlanDefinition`) |
| POST | `/plans/switch` | B2B | `{plan_id, billing_cycle}` — narx hisoblanadi, `price > 0` bo'lsa wallet'dan yechiladi, `PlanPurchase` yoziladi, `user.current_plan_id` yangilanadi |
| GET | `/plans/history` | B2B | O'z tarif sotib olish tarixi, sahifalab |

## Service funksiyalari (`app/modules/plans/service.py`)

```python
async def switch_plan(db, user, plan_id, billing_cycle) -> tuple[User, PlanPurchase]:
    if plan_id == (user.current_plan_id or PlanId.free):
        raise ConflictError("Siz allaqachon shu tarifdasiz")

    definition = PLAN_CATALOG[plan_id]  # noto'g'ri plan_id — 422 (schema darajasida enum bilan avtomatik)
    price = pricing.yearly_price(definition.price) if billing_cycle == BillingCycle.yearly else definition.price

    if price > 0:
        await wallet_service.pay(
            db, user, price, f"Tarif sotib olindi — {definition.name}",
            kind=WalletTxKind.plan, ref=plan_id.value,
        )

    user.current_plan_id = plan_id.value
    purchase = PlanPurchase(user_id=user.id, plan_id=plan_id, billing_cycle=billing_cycle, price_paid=price)
    db.add(purchase)
    await db.commit()
    await db.refresh(user)
    await db.refresh(purchase)
    return user, purchase
```

`wallet_service.pay()` balans yetmasa avtomatik `ConflictError` (409) ko'taradi — mavjud xatti-harakat qayta ishlatiladi.

## Validatsiya

`PlanSwitchRequest`: `plan_id: PlanId`, `billing_cycle: BillingCycle = BillingCycle.monthly` — noto'g'ri `plan_id` qiymati Pydantic enum orqali avtomatik 422 beradi (frontend `planById()`dagi "noma'lum id → free" fallback'idan farqli — backend qattiqroq: yaroqsiz ID'ni sokin `free`ga aylantirish o'rniga rad etadi, bu moliyaviy operatsiya uchun to'g'ri xatti-harakat).

## Test strategiyasi

`tests/test_plans.py`:
1. `GET /plans` — 4 ta tarif, har birida `yearly_price` to'g'ri hisoblangan (`round(price*12*0.84)`)
2. `POST /plans/switch` — pullik tarifga o'tish: wallet balansi kamayadi, `current_plan_id` yangilanadi, `PlanPurchase` yoziladi
3. Balans yetmasa — 409, `current_plan_id` o'zgarmaydi, `PlanPurchase` yozilmaydi
4. Bepul tarifga o'tish — wallet'ga tegilmaydi (`price=0`), baribir `PlanPurchase` yoziladi (`price_paid=0`)
5. Joriy tarifga qayta "o'tish" — 409
6. Yillik `billing_cycle` — narx to'g'ri hisoblanadi va shundan yechiladi
7. `GET /plans/mine` — joriy tarif to'g'ri qaytadi (yangi B2B userда standart `free`)
8. `GET /plans/history` — sahifalab, faqat o'ziniki
9. B2C user `/plans/switch`ga urinsa — 403

## Migratsiya

`alembic revision --autogenerate -m "plan_purchases jadvali va wallet_tx_kind ga plan qo'shish"`. Ikkita alohida DDL: yangi jadval (avtomatik aniqlanadi) + mavjud `wallet_tx_kind` enumiga yangi qiymat (`ALTER TYPE ... ADD VALUE` — Postgres'da bu tranzaksiyada alohida commit talab qilishi mumkin, generatsiya qilingan faylni tekshirish kerak).

## Doiradan tashqari

- Cheklovlarni haqiqiy kuchga kiritish (`photo_limit`/`video_limit`/e'lonlar soni) — frontendda hech qanday shaklda mavjud emas
- Muddat/avtomatik yangilanish/avtomatik pasaytirish
- Promotion (reklama paketi, `ListingPromo`) — allaqachon Listings/Tours/Guides specларда alohida qoldirilgan, bu yerda ham aralashtirilmaydi
- Biznes toifasiga qarab farqlanadigan tariflar (frontendda barcha B2B rollar bir xil 4 ta tarifni ko'radi)
