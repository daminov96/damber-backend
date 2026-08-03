# Frontend yangilanishi (front0308) — backend'ni moslashtirish rejasi

**Sana**: 2026-08-03
**Holat**: Amalga oshirildi, testlar bilan tekshirildi (186 test)

## Kontekst

Foydalanuvchi frontend'ning eng yangi versiyasini (`~/Desktop/projects/damber/front/front0308/damber-front`, haqiqiy git repo, 117 commit) tekshirishni so'radi — biz backend qurgan versiya (`front2807`) bilan solishtirib, kerakli backend o'zgarishlarini aniqlash uchun. To'liq diff (`diff -rq`) + 3 ta parallel Explore agent tadqiqoti (chat/auth/admin, operators/tours katalogi, listings/wallet/plans) o'tkazildi.

**Asosiy xulosa**: deyarli barcha fayl o'zgargan bo'lsa-da, bu asosan **frontend-ichki taqdimot qayta qurilishi** (yangi operators/tours katalog sahifalari, UI qayta dizayni) — bizning backend ma'lumot modeliga ta'sir qilmaydi. Chat va Admin butunlay o'zgarmagan (hali ham dekorativ). Haqiqiy backend ishi talab qiladigan aniq uchta narsa topildi, foydalanuvchi bilan kelishilgan tartibda barchasi shu sessiyada bajariladi:

1. **Tarif obunasi tsikli** (`plans` + `users`) — eng katta topilma: frontendda endi `planUntil`/`planPeriod`/`planRate` bilan **haqiqiy proratsiya hisob-kitobi** bor (`src/lib/planBilling.ts`, testlar bilan qoplangan, "backend ham aynan shu formulani takrorlashi kerak" deb hujjatlashtirilgan).
2. **Listing: yangi `Aqua` turi** + `old_price` ustuni (Tour'dagi mavjud naqshga mos).
3. **Qidiruv filtri kengaytmalari** — `tours`/`operators` `search()`ga bir nechta yangi parametr (narx chegarasi, chegirma, reyting).

**Doiradan tashqari qoldirilgan narsalar** (tadqiqot bilan asoslangan):
- Chat, Admin/superadmin panel — o'zgarmagan, hamon to'liq dekorativ mock.
- Wallet, to'lov usullari (`paymentMethods.ts`) — faqat vizual, ma'lumot shakli o'zgarmagan.
- `atm_banks`/`nearby_exchanges` (yangi Hotel/Sanatorium maydonlari) va Dining'ning yangi qoida maydonlari (alkogol/halol/dress-code va h.k.) — bularning barchasi bizning **allaqachon ochiq** `Listing.extra: JSONB` maydoniga (validatsiyasiz dict) to'g'ridan-to'g'ri sig'adi — **hech qanday backend o'zgarishi shart emas**, faqat tasdiqlash uchun eslatib o'tildi.
- `landmarks.ts`/`distances.ts` (masofa hisoblash) — to'liq client tomonda, mavjud `coords` maydonidan hisoblanadi.
- Qidiruv filtrlarining `month`/`scope` (mamlakat ichi/tashqi)/`with_tours_only`/`experience` qismlari — bular `extra` JSONB ichidagi tuzilmani (departures/stops) qidirishni talab qiladi, hozircha frontend hali real API'ga ulanmagani uchun **keyingi bosqichga qoldiriladi** (faqat narx/reyting/chegirma kabi to'g'ridan-to'g'ri ustunlarga asoslangan filtrlar qo'shiladi).
- `OperatorReviews.tsx` — operator profiliga sharh UI'si paydo bo'lgan, lekin bu **to'liq frontend-mock** (localStorage `useReviews` do'koni, hech qanday API chaqiruvisiz) — bizning `reviews` moduli ataylab faqat Listing/Tour bilan cheklangan, bu qaror o'zgarmaydi, faqat mahsulot darajasidagi kelajakdagi savol sifatida qayd etiladi.
- `TourOperator`ning yangi `bizForm`/`legalAddress`/`legalDistrict`/`certified`/`cancellationPolicy` maydonlari — bularning barchasi **faqat GID profiliga tegishli** (`GuideWizard.tsx` orqali to'ldiriladi, `OperatorWizard.tsx` hech qachon yozmaydi) — `operators` moduli doirasidan tashqarida, `guides` moduliga aloqasi bo'lsa ham hozircha frontendda hech qayerda gid uchun ham to'ldirilmagan yangi majburiy talab yo'q.

## 1-qism: Tarif obunasi tsikli

### Frontend formula (`src/lib/planBilling.ts`, to'liq o'qildi)

```
mode = !hasActivePlan ? "new" : isSamePlan ? "extend" : "switch"
daysAdded = period === "monthly" ? 30 : 365
refundable = hasActivePlan ? round(rate * daysLeft) : 0
refund = mode === "switch" ? refundable : 0
payable = max(0, cost - refund)
newRate = (mode === "extend" && daysLeft > 0)
    ? (refundable + cost) / (daysLeft + daysAdded)
    : cost / daysAdded
newUntil = (mode === "extend" ? currentPlanUntil : today) + daysAdded kun
```
`hasActivePlan = currentPlanId != "free" AND planUntil bor AND planUntil >= bugun` — **lazy-expiry**: muddati o'tgan tarif avtomatik "amaldagi emas" hisoblanadi, hech qanday cron/scheduled job shart emas (frontendda ham yo'q — `HostPlansTab.tsx` shunchaki har safar o'qishda solishtiradi).

To'lov ketma-ketligi (`HostPlansTab.tsx::confirm()`): **avval qaytim** (agar `refund > 0`) hamyonga kredit qilinadi, **keyin** yangi narx yechiladi — bu ikkalasi alohida ledger yozuvi (nizoda tushunarli bo'lishi uchun, izoh: "ikkalasi ham ledgerda alohida yozuv bo'lib qoladi"). Agar to'lov muvaffaqiyatsiz bo'lsa ham, qaytim orqaga qaytarilmaydi (bu — foydalanuvchiga tegishli haqiqiy pul, frontend ham buni qaytarmaydi).

Bir xil tarifni qayta tanlash endi **taqiqlanmaydi** — bu "uzaytirish" (extend) sifatida ishlaydi (bizning hozirgi backend'dagi `ConflictError("Siz allaqachon shu tarifdasiz")` OLIB TASHLANADI — bu ataylab qilingan xulq-atvor o'zgarishi, yangi frontend mantig'iga mos).

`listingLimit` (bepul:1, standart:3, biznes:7, premium:15) — katalogga **faqat ma'lumot sifatida** qo'shiladi (bizning `catalog.py`dagi matnda bu raqamlar allaqachon bor: "3 ta e'lon joylashtirish" va h.k.). **Kuchga kiritish (limitdan oshgan e'lonlarni avtomatik pauza qilish) qo'shilmaydi** — frontendda bu hali ham faqat ogohlantiruvchi matn (`HostPlansTab.tsx:529-539`), hech qayerda dasturiy ravishda amalga oshirilmagan (grep bilan tasdiqlangan — `listingLimit` faqat shu matn va katalogda ishlatiladi). Bu — mavjud "Cheklovlar kuchga kiritilmaydi" qarorining davomi (`plans` moduli spec'ida allaqachon hujjatlashtirilgan).

### O'zgarishlar

**`app/modules/plans/models.py`**: `BillingCycle` enum klassi **`app/modules/users/models.py`ga ko'chiriladi** (arxitektura tozaligi uchun — `plan_period` endi `User`ning o'z maydoni, `users` — bazaviy modul, `plans` esa unga bog'liq bo'lgan yuqori darajali modul; hozirgi holatda `users`ning `plans`ga bog'liq bo'lishi noto'g'ri yo'nalish bo'lardi). `plans/models.py` endi `from app.modules.users.models import BillingCycle` qiladi. Postgres enum turi nomi bir xil qoladi (`plan_billing_cycle`) — shuning uchun `User.plan_period` shu turni **qayta ishlatadi** (`create_type=False`, migratsiya faylida qo'lda tuzatiladi — bu sessiyada bir necha marta uchragan tanish naqsh).

**`app/modules/users/models.py`** — `User` klassiga qo'shiladi:
```python
plan_until: Mapped[date | None] = mapped_column(Date, nullable=True)
plan_period: Mapped[BillingCycle | None] = mapped_column(
    Enum(BillingCycle, name="plan_billing_cycle"), nullable=True
)
plan_rate: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
```
(`BillingCycle` shu faylda endi e'lon qilinadi — yuqorida.)

**`app/modules/plans/catalog.py`**: `PlanDefinition`ga `listing_limit: int` qo'shiladi; 4 ta tarifga qiymat: free=1, standard=3, business=7, premium=15.

**`app/modules/plans/service.py::switch_plan()`** — to'liq qayta yoziladi, yuqoridagi formula asosida:
```python
async def switch_plan(db, user, plan_id, billing_cycle) -> tuple[User, PlanPurchase]:
    if plan_id == PlanId.free:
        raise ConflictError("Bepul tarifni sotib olib bo'lmaydi — bu standart holat")

    definition = PLAN_CATALOG[plan_id]
    cost = yearly_price(definition.price) if billing_cycle == BillingCycle.yearly else definition.price
    today = date.today()

    has_active_plan = (
        user.current_plan_id not in (None, PlanId.free.value)
        and user.plan_until is not None
        and user.plan_until >= today
    )
    days_left = max(0, (user.plan_until - today).days) if has_active_plan else 0
    rate = float(user.plan_rate or 0)
    days_added = 30 if billing_cycle == BillingCycle.monthly else 365
    is_same_plan = has_active_plan and plan_id.value == user.current_plan_id
    mode = "new" if not has_active_plan else ("extend" if is_same_plan else "switch")

    refundable = round(rate * days_left) if has_active_plan else 0
    refund = refundable if mode == "switch" else 0
    payable = max(0, cost - refund)
    new_rate = (
        (refundable + cost) / (days_left + days_added)
        if mode == "extend" and days_left > 0
        else cost / days_added
    )
    base_date = user.plan_until if mode == "extend" else today
    new_until = base_date + timedelta(days=days_added)

    if refund > 0:
        await wallet_service.credit(
            db, user, refund, f"Tarif almashtirildi — {days_left} kun qaytarildi",
            kind=WalletTxKind.plan, ref=plan_id.value,
        )
    if payable > 0:
        label = "Tarif uzaytirildi" if mode == "extend" else "Tarif sotib olindi"
        await wallet_service.pay(
            db, user, payable, f"{label} — {definition.name}",
            kind=WalletTxKind.plan, ref=plan_id.value,
        )

    user.current_plan_id = plan_id.value
    user.plan_until = new_until
    user.plan_period = billing_cycle
    user.plan_rate = new_rate
    purchase = PlanPurchase(user_id=user.id, plan_id=plan_id, billing_cycle=billing_cycle, price_paid=payable)
    db.add(purchase)
    await db.commit()
    await db.refresh(user)
    await db.refresh(purchase)
    return user, purchase
```
`wallet_service.credit()`/`pay()` — mavjud funksiyalar (`app/modules/wallet/service.py`), o'zgarishsiz qayta ishlatiladi. `refund > 0` bo'lib, keyin `pay()` `ConflictError` (409) tashlasa — qaytim allaqachon commit qilingan bo'lib qoladi (bu **ataylab**, frontenddagi xatti-harakatga mos: qaytim foydalanuvchiga tegishli pul, muvaffaqiyatsiz urinish uni yo'qotmaydi).

**`get_my_plan()`** — muddati o'tgan tarifni "amaldagi emas" deb hisoblash uchun yangilanadi (DB'dagi `current_plan_id`ni o'zgartirmaydi — faqat javobda "amaldagi" holatni hisoblaydi, frontenddagi kabi):
```python
def _effective_plan_id(user: User, today: date) -> PlanId:
    if user.current_plan_id and user.current_plan_id != PlanId.free.value:
        if user.plan_until and user.plan_until >= today:
            return PlanId(user.current_plan_id)
    return PlanId.free

def get_my_plan(user: User) -> MyPlanOut:
    today = date.today()
    effective_id = _effective_plan_id(user, today)
    days_left = max(0, (user.plan_until - today).days) if user.plan_until else 0
    return MyPlanOut(
        current_plan_id=effective_id,
        plan=_to_plan_out(PLAN_CATALOG[effective_id]),
        plan_until=user.plan_until,
        plan_period=user.plan_period,
        plan_rate=float(user.plan_rate) if user.plan_rate is not None else None,
        days_left=days_left,
    )
```

**`app/modules/plans/schemas.py`**: `PlanOut`ga `listing_limit: int`; `MyPlanOut`ga `plan_until: date | None`, `plan_period: BillingCycle | None`, `plan_rate: float | None`, `days_left: int`; `BillingCycle` importi endi `app.modules.users.models`dan.

**`app/modules/plans/router.py`** — o'zgarishsiz qoladi (mavjud `POST /plans/switch` va `GET /plans/mine` endpointlari yangi service mantig'ini avtomatik ishlatadi; alohida "quote" (oldindan hisoblash) endpoint **qo'shilmaydi** — frontend buni `GET /plans` (narx) + `GET /plans/mine` (joriy holat: `plan_until`/`plan_rate`/`days_left`) + `GET /users/me` (hamyon balansi)dan olingan ma'lumot bilan o'zi hisoblay oladi, xuddi hozir `planBilling.ts` qilayotgani kabi — ortiqcha endpoint kerak emas).

## 2-qism: Listing — `Aqua` turi + `old_price`

**`app/modules/listings/models.py`**: `ListingType`ga `Aqua = "Aqua"` qo'shiladi (basseyn/sauna/akvapark). `Listing`ga:
```python
old_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
```
(Tour'dagi `old_price` naqshiga mos — u yerda `default=0`, lekin Listing uchun `nullable=True` to'g'riroq, chunki aksariyat listingda chegirma yo'q va frontend buni ixtiyoriy (`oldPrice?: number`) deb belgilagan.)

**`app/modules/listings/schemas.py`**: `ListingCreateRequest`/`ListingUpdateRequest`/`ListingOut`ga `old_price: float | None = None` qo'shiladi.

`atm_banks`/`nearby_exchanges` va Dining'ning yangi maydonlari — **hech qanday kod o'zgarishi kerak emas** (yuqorida asoslangan, `extra: dict` orqali ishlaydi) — faqat tezkor tekshiruv: mavjud `test_listings.py`da `extra` maydoniga ixtiyoriy tuzilma yozib, qayta o'qib tasdiqlash (mavjud testlar allaqachon buni bilvosita qamrab oladi, alohida test shart emas).

## 3-qism: Qidiruv filtri kengaytmalari

**`app/modules/tours/service.py::search()`** — yangi parametrlar: `max_price: float | None`, `discount_only: bool | None` (shart: `Tour.old_price > 0 AND Tour.old_price > Tour.price`), mavjud `Tour.price`/`Tour.old_price` ustunlaridan foydalanadi.

**`app/modules/operators/service.py::search()`** — yangi parametr: `min_rating: float | None` (`TourOperator.rating >= min_rating`), mavjud `rating` ustunidan.

Ikkala `router.py`ga mos `Query(None)` parametrlari qo'shiladi, xuddi mavjud `nights_min`/`nights_max` naqshiga o'xshab.

`month`/`scope`/`with_tours_only`/`experience` — **bu sessiyada qo'shilmaydi** (yuqorida asoslangan — `extra` JSONB ichini qidirish talab qiladi, frontend hali ulanmagan).

## Qurilish tartibi

1. `users/models.py` — `BillingCycle` ko'chiriladi, `plan_until`/`plan_period`/`plan_rate` qo'shiladi
2. `plans/models.py`/`schemas.py`/`catalog.py` — import tuzatiladi, `listing_limit` qo'shiladi
3. `plans/service.py::switch_plan()`/`get_my_plan()` — to'liq qayta yoziladi
4. `listings/models.py`/`schemas.py` — `Aqua`, `old_price`
5. `tours/service.py`/`router.py` — `max_price`, `discount_only`
6. `operators/service.py`/`router.py` — `min_rating`
7. Alembic migratsiya (`alembic revision --autogenerate`) — kutilgan: `users`ga 3 ustun (`plan_period` uchun `create_type=False` qo'lda tuzatiladi, mavjud `PlanPurchase.billing_cycle`dan meros — mavjud qatorlar uchun `nullable=True` bo'lgani sababli `server_default` shart emas), `listings`ga `old_price` ustuni + `listing_type` enumiga `Aqua` qiymati qo'shish (`ALTER TYPE ... ADD VALUE` — qo'lda, avtogenerate buni ham avtomatik qilmaydi, `WalletTxKind.plan` qo'shilganda ishlatilgan naqsh takrorlanadi)
8. `alembic upgrade head`
9. Testlar: `tests/test_plans.py`ga qo'shimcha — yangi/uzaytirish/almashtirish (3 mode), muddati o'tgan tarif "free" deb hisoblanishi, qaytim+to'lov ketma-ketligi, bir xil tarifni qayta tanlash (endi ConflictError emas, extend); `tests/test_listings.py`ga `Aqua` turi bilan yaratish + `old_price`; `tests/test_tours.py`/`test_operators.py`ga yangi filtr parametrlari testi
10. `ruff check`, `pytest` (to'liq to'plam), curl smoke-test (yangi tarif sotib olish → muddatidan oldin uzaytirish → boshqa tarifga almashtirish va qaytim tekshirish → muddatini "o'tkazib" free holatga qaytishni tekshirish)
11. Muvaffaqiyatli bo'lsa — commit + push (foydalanuvchi so'raganda)

## Muhim fayllar

- `app/modules/users/models.py`, `app/modules/plans/{models,schemas,catalog,service}.py` (1-qism)
- `app/modules/listings/{models,schemas}.py` (2-qism)
- `app/modules/tours/{service,router}.py`, `app/modules/operators/{service,router}.py` (3-qism)
- `tests/test_plans.py`, `tests/test_listings.py`, `tests/test_tours.py`, `tests/test_operators.py`
- Namuna: `app/modules/tours/models.py` (`old_price`/`price` naqshi), `app/modules/wallet/service.py` (`pay`/`credit`), avvalgi migratsiyalardagi `create_type=False` va `ALTER TYPE ... ADD VALUE` naqshlari (`operators`/`tours`/`guides`/`rent_companies` migratsiyalari, `wallet`ning `plan` qiymati qo'shilgan migratsiyasi)

## Tekshirish (Verification)

1. `docker compose exec api ruff check .`
2. `docker compose exec api pytest`
3. Curl smoke-test: B2B user standart tarifni sotib oladi (`mode=new`) → bir necha kundan keyin (test uchun DB orqali `plan_until` orqaga suriladi) xuddi shu tarifni uzaytiradi (`mode=extend`, qaytim yo'q, kunlar qo'shiladi) → keyin biznes tarifga o'tadi (`mode=switch`, qaytim hisoblanadi va hamyonga tushadi) → `GET /plans/mine` orqali `days_left`/`plan_rate` to'g'riligini tekshirish → Aqua turida listing yaratish va `old_price` bilan qidiruvda ko'rinishini tekshirish → `GET /tours?max_price=...&discount_only=true` va `GET /operators?min_rating=...` filtrlarini tekshirish
4. Muvaffaqiyatli bo'lsa — commit + push (foydalanuvchi so'raganda)
