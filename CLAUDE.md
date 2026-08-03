## Loyiha holati (2026-08-03)

Backend qurilishi bosqichma-bosqich davom etmoqda. Frontend manbasi
(lokal, rabochiy stolda) — **eng yangi versiya**:
`~/Desktop/projects/damber/front/front0308/damber-front` (haqiqiy git repo,
`github.com/daminov96/damber-front`, 117+ commit; avvalgi `front2807`
versiyasi endi eskirgan — backend shu versiyadan kelib chiqib qurilgan
edi, 2026-08-03 sessiyasida `front0308`ga to'liq solishtirib moslashtirildi,
pastga qarang). Next.js, hozircha to'liq localStorage-mock, haqiqiy API
chaqiruvi yo'q — `src/lib/api.ts` va Zustand store'lar backend contract'ini
belgilaydi.

**Tayyor modullar:**
- `users` — register/login/me, JWT, rollar (B2C/B2B/ADMIN)
- `listings` — CRUD, qidiruv/filtr, rasm yuklash (LocalDiskStorage),
  ADMIN moderatsiyasi. Spec: `docs/superpowers/specs/2026-07-24-listings-module-design.md`
- `wallet` — balans (users.wallet_balance source of truth), topup,
  tarix, `pay()`/`credit()`/`transfer()` (faqat ichki chaqiruv uchun,
  public endpoint yo'q). Spec: `docs/superpowers/specs/2026-07-24-wallet-module-design.md`
- `bookings` — narx hisoblash (hafta ichi/dam olish/mavsumiy ustama/
  aksiya/promo kod, `app/modules/bookings/pricing.py`), avans FAQAT
  wallet orqali, eskrov (`held→released/refunded`), holat sikli
  (pending→confirmed→completed, yoki rejected/cancelled), siyosat-
  asosli qaytarish (flexible/moderate/strict/nonref), band sanalar/
  min_stay/capacity/kesishuv tekshiruvi. Spec:
  `docs/superpowers/specs/2026-07-28-bookings-module-design.md`.
  Commit qilingan.
- `operators` — tur operatori KOMPANIYA profillari (`kind: "guide"`
  gid profillari doiradan tashqari — keyingi bosqich). Moderatsiyasiz,
  frontendga mos (Listings'dan farqli — `verified` yo'q). `tin`
  9-raqamli validatsiya, `license_issued` serverda avtomatik hosil
  qilinadi, rasm yuklash Listings pattern'ini qayta ishlatadi
  (`TourOperatorPhoto` + `StoragePort`). `region` ustuni `listings`
  jadvali yaratgan `listing_region` Postgres enum turini qayta
  ishlatadi (`create_type=False` — migratsiya faylida qo'lda tuzatildi,
  avtogenerate ikkinchi marta CREATE TYPE qilishga urinadi). Spec:
  `docs/superpowers/specs/2026-07-28-operators-module-design.md`.
  Commit qilingan.
- `tours` — operator profiliga bog'langan turlar (`operator_id`),
  Listings'dagi kabi `pending`/ADMIN approve moderatsiyasi (Operators'dan
  farqli). Murakkab ichki tuzilmalar (itinerary/stops/priceTiers/
  departures/faq) `extra` JSONB'da. `TourBooking` — TO'LOVSIZ oddiy
  so'rov/lead-capture (ism/telefon/odam soni, `total_estimate` faqat
  ko'rsatish uchun), xost `confirm`/`reject` qiladi — eskrov/wallet
  ALOQASI YO'Q (frontendda ham yo'q, foydalanuvchi bilan tasdiqlangan).
  Reklama/promo to'lov oqimi (`TourActivation`) doiradan tashqari —
  Listings uchun ham hali qurilmagan. `region` yana `create_type=False`
  bilan tuzatildi. Spec: `docs/superpowers/specs/2026-07-28-tours-module-design.md`.
  Commit qilingan va GitHub'ga push qilingan (2026-07-28).
- `rent_companies` — ijara kompaniya profillari, Operators bilan bir
  xil: moderatsiyasiz, `tin` majburiy. `license_doc_name` esa Operators'dan
  farqli — MAJBURIY (wizard fayl talab qiladi). `pickup_zones`/
  `payment_methods` — kamida 1 ta (Pydantic `Field(min_length=1)`).
  **`listings` moduliga o'zgartirish**: `Listing.company_id` (ixtiyoriy,
  `ON DELETE SET NULL`) qo'shildi — kompaniya o'chirilsa mashina
  saqlanadi, faqat bog'lanish uziladi; xost aniq tanlaydi (frontenddagi
  "har doim avtomatik bog'lash" xatosi takrorlanmadi), backend
  egalik+`type==RentCar` tekshiradi. `GET /rent-companies/{id}/listings`
  qo'shildi (frontendda yo'q edi, izchillik uchun qo'shildi).
  **Yon-bug tuzatildi**: `operators/service.py::delete()` turlari mavjud
  operatorni o'chirishda avval xom 500 qaytarardi (`Tour.operator_id`
  FK `RESTRICT`), endi oldindan tekshirib toza 409 qaytaradi. Spec:
  `docs/superpowers/specs/2026-07-29-rent-companies-module-design.md`.
  Commit qilingan va GitHub'ga push qilingan (2026-07-29).
- `guides` — yakka gid profillari, **Operators bilan bitta jadvalda
  emas** (frontendda `TourOperator.kind:"guide"` sifatida bitta
  jadvalda, lekin bu — sparse-table antipattern bo'lardi, deyarli
  umumiy maydon yo'q — shuning uchun mustaqil `guides` jadvali
  tanlandi). `certified` mijozdan qabul qilinmaydi — serverda
  `license_doc_name is not None`dan hisoblanadi. **`tours` moduliga
  o'zgartirish**: `Tour.operator_id` endi ixtiyoriy, yangi ixtiyoriy
  `Tour.guide_id` qo'shildi, DB CHECK constraint — aynan bittasi
  to'ldirilgan bo'lishi shart (polimorfik egalik, autogenerate
  buni avtomatik aniqlamaydi — qo'lda qo'shildi). Guide o'chirishda
  ham operators'dagi tuzatilgan pattern (bog'liq turlar bo'lsa 409).
  Spec: `docs/superpowers/specs/2026-07-29-guides-module-design.md`.
  Commit qilingan va GitHub'ga push qilingan (2026-07-29).
- `reviews` — FAQAT Listing va Tour uchun (Operators/Guides/RentCompanies'da
  sharh tushunchasi frontendda mutlaqo yo'q — kengaytirilmadi). Polimorfik
  nishon Tours'dagi `operator_id`/`guide_id` naqshi bilan bir xil:
  `listing_id`/`tour_id` (DB CHECK — aynan bittasi). **Listing sharhi —
  HAQIQIY bron-gating**: `booking_id` majburiy, `status == completed`,
  egalik tekshiriladi, bitta bronga bitta sharh (frontendda niyat aniq —
  dashboard "Baholash" tugmasi — lekin hech qayerda majburiy qilinmagan
  edi, backend'da haqiqiy qilindi). **Tur sharhi — bronga bog'lanmaydi**
  (`TourBooking`da "yakunlandi" tushunchasi umuman yo'q), `verified`
  doim `False`, bitta user — bitta tur — bitta sharh. **`rating`/
  `rating_count` endi serverda haqiqiy qayta hisoblanadi**
  (`listings/service.py::recompute_rating()`, `tours/service.py::recompute_rating()`
  — Reviews nishon holatini to'g'ridan-to'g'ri o'zgartirmaydi, tor
  funksiya orqali chaqiradi) — frontendda bu hech qachon bo'lmagan
  ("jonli ko'ringan, aslida statik" maydon, Guide'dagi `certified`
  bilan bir xil holat edi). Spec:
  `docs/superpowers/specs/2026-07-29-reviews-module-design.md`.
  Commit qilingan va GitHub'ga push qilingan (2026-07-29).
- `plans` — B2B tarif rejalari, **statik Python katalog** (`plans/catalog.py`
  — DB jadvali emas, `PROMO_CODES` naqshiga o'xshab, 4 ta qat'iy tarif:
  `free`/`standard`/`business`/`premium`, frontend `data/plans.ts`dan
  so'z-ma-so'z ko'chirilgan). **Cheklovlar (photoLimit/videoLimit/e'lon
  soni) kuchga kiritilmaydi** — frontendda bu hatto UI darajasida ham
  amalga oshirilmagan (Review'dagi bron-gating'dan farqli — bu yerda
  hech qanday niyat izi yo'q), shuning uchun o'ylab topilmadi, faqat
  katalog API orqali chiqariladi. `PlanPurchase` audit jadvali qo'shildi
  (frontendda yo'q — moliyaviy operatsiya uchun tarix kerak).
  `WalletTxKind`ga `plan` qiymati qo'shildi (frontend buni umumiy
  `"promo"` bilan chalkashtiradi). Yillik narx — saqlanadigan maydon
  emas, `round(oylik*12*0.84)` hisoblash. Muddat/yangilanish yo'q
  (frontendda umuman yo'q). Spec:
  `docs/superpowers/specs/2026-07-30-plans-module-design.md`.
  Commit qilingan va GitHub'ga push qilingan (2026-07-30).
- `admin` — to'liq admin panel. Frontend tadqiqoti shuni ko'rsatdi:
  "Admin panel"ning katta qismi dekorativ (Trafik tahlili qattiq
  kodlangan, 2FA/Xavfsizlik soxta, "Adminlar jamoasi" autentifikatsiyaga
  bog'lanmagan) — bular DOIRADAN TASHQARI qoldirildi. **Xavfsizlik
  teshigi topildi va tuzatildi**: `POST /auth/register`da `role`
  cheklovsiz edi — istalgan kishi `role:"ADMIN"` yuborib to'liq admin
  huquqi ola olardi (`RegisterRequest.role: Literal[B2C, B2B]` bilan
  yopildi). **Moderatsiyada "rad etish" haqiqiy soft-status sifatida
  qurildi** — `Listing`/`Tour`ga `rejected`/`reject_reason` qo'shildi
  (frontendda rad etish o'chirish bilan aralashtirilgan edi, bu yerda
  Bookings'dagi `reject_reason` patterni takrorlandi); tasdiqlangan
  yozuvni rad etishga urinish 409 qaytaradi. `User.is_banned`/
  `banned_reason` — yangi, backend-only (frontendda yo'q, lekin "to'liq
  panel" uchun zarur) — `get_current_user()` va `authenticate()`da
  kuchga kiritiladi (bloklangan user login qila olmaydi, mavjud token
  ham darhol ishlamay qoladi). `invite-admin` — "Adminlar jamoasi"ning
  ishlaydigan versiyasi (haqiqiy foydalanuvchi yaratadi, `role=ADMIN`
  bilan). `AdminAuditLog` — frontenddagi `addLog()` naqshining server
  tomon versiyasi, `admin/service.py::log_action()` boshqa modullar
  (`listings`/`tours` router'lari) tomonidan chaqiriladi — `admin.service`
  faqat modellarga bog'liq (`users`/`listings`/`tours`/`bookings`),
  boshqa `.service`larga bog'liq emas — aylanma import yo'q. Dashboard
  statistikasi haqiqiy agregatsiya (`func.count`/`func.sum`). Spec:
  `docs/superpowers/specs/2026-07-30-admin-module-design.md`.
  Commit qilingan va GitHub'ga push qilingan (2026-07-30).
- `chat` — listing egasi bilan xabarlashuv. Frontend tadqiqoti (`src/store/chat.ts`,
  `ChatThread.tsx`, `ListingChat.tsx`, `ClientChats.tsx`, `HostChats.tsx`)
  shuni ko'rsatdi: bu loyihadagi eng kam sonli **dekorativ bo'lmagan**
  funksiyalardan biri — to'liq ishlaydi, real navigatsiyaga ulangan, o'z
  test to'plami bor. **WebSocket qo'shilmadi** — frontend hech qachon
  haqiqiy real-time talab qilmagan (yagona "jonlilik" — `setTimeout(2000ms)`
  soxta bot javobi, faqat demo uchun); oddiy REST yetarli deb topildi.
  Suhbat frontendga mos ravishda **client+owner juftligi bilan aniqlanadi**
  (`UniqueConstraint(client_id, owner_id)`), listingga bog'lanmagan (bitta
  egaga turli listinglar haqida yozsa ham bitta thread) — lekin `listing_id`
  ixtiyoriy kelib chiqish konteksti sifatida saqlanadi. **`owner_id` klientdan
  qabul qilinmaydi** — `POST /chat/conversations` faqat `listing_id` oladi,
  owner shu listingdan serverda hosil qilinadi (Wallet/Reviews'dagi
  "server-side authoritative" naqshi). **Xabar modeli "haqiqiy" qilindi**:
  frontendda `{sender, text, time}` (ID yo'q, chin timestamp yo'q, o'qilgan/
  o'qilmagan thread darajasida) — backend'da har xabarda `id`/`created_at`/
  **xabar darajasidagi** `read_at` (Reviews'dagi `rating`/`certified` bilan
  bir xil "jonli ko'ringan, aslida qo'pol narsani to'g'irlash" naqshi).
  **Sezgir ma'lumot filtri** (`detectSensitiveData` — frontendda faqat
  client tomonda, bypass qilinardi) serverda ham kuchga kiritildi — telefon/
  karta raqami reglar bilan aniqlansa 400 qaytaradi. O'z listingiga yozish —
  409. Faqat ishtirokchilar ko'ra oladi, **ADMIN uchun ham maxsus bypass
  yo'q** (frontendda adminning chatga aloqasi umuman yo'q edi). Turlar/
  operatorlar/gidlarga ulanmagan (frontendda faqat Listing domenida). Spec:
  `docs/superpowers/specs/2026-07-30-chat-module-design.md`.
  Commit qilinmagan/push qilinmagan hali (foydalanuvchi so'raganda).

**Rejalashtirilgan asosiy modullar ketma-ketligi to'liq tugadi**: `users` →
`listings` → `wallet` → `bookings` → `operators` → `tours` →
`rent_companies` → `guides` → `reviews` → `plans` → `admin` → `chat` —
barchasi tayyor, test qilingan, curl smoke-test bilan tekshirilgan.

### Frontend `front0308`ga moslashtirish (2026-08-03)

Foydalanuvchi so'ragan: eng yangi frontend versiyasini (`front0308`)
`front2807` bilan to'liq solishtirib, kerakli backend o'zgarishlarini
aniqlash. `diff -rq` + 3 ta parallel Explore agent tadqiqoti (chat/auth/
admin, operators/tours katalogi qayta qurilishi, listings/wallet/plans)
o'tkazildi. **Asosiy xulosa**: deyarli barcha fayl o'zgargan bo'lsa-da,
bu asosan frontend-ichki taqdimot qayta qurilishi (yangi operators/tours
katalog sahifalari) — Chat va Admin **butunlay o'zgarmagan** (hamon
dekorativ). Uchta haqiqiy backend ishi topildi va bajarildi:

1. **Tarif obunasi tsikli** (eng katta topilma) — frontendda
   `planUntil`/`planPeriod`/`planRate` bilan haqiqiy proratsiya hisob-
   kitobi paydo bo'lgan (`src/lib/planBilling.ts`, testlar bilan
   qoplangan, "backend aynan shu formulani takrorlashi kerak" deb
   hujjatlashtirilgan). `User`ga `plan_until`/`plan_period`/`plan_rate`
   qo'shildi (`BillingCycle` enum `plans/models.py`dan `users/models.py`ga
   ko'chirildi — arxitektura tozaligi uchun, `users` bazaviy modul
   `plans`ga bog'liq bo'lmasligi kerak, Postgres enum turi qayta
   ishlatiladi). `plans/service.py::switch_plan()` to'liq qayta yozildi:
   uch rejim — **yangi** (`hasActivePlan=False`), **uzaytirish**
   (`extend` — bir xil tarif qayta tanlansa, qaytim yo'q, kunlar
   yonmaydi, muddat mavjud tugash sanasidan boshlanadi), **almashtirish**
   (`switch` — boshqa tarif, qolgan kunlar puli `rate × daysLeft`
   sifatida hamyonga qaytariladi, TO'LIQ narx keyin yechiladi — netted
   emas, ikkalasi alohida ledger yozuvi). **Muhim tuzatish**: dastlab
   `payable` (net) summani yechish rejalashtirilgan edi, lekin frontend
   formulasini qayta tekshirganda bu noto'g'ri balans tekshiruvi berishi
   aniqlandi (`balans + refund >= payable` — juda yumshoq shart);
   to'g'ri yechim — TO'LIQ `cost`ni yechish, `wallet_service.pay()`ning
   o'zi balansni (qaytim qo'shilgandan keyin) tekshiradi. Bir xil
   tarifni qayta tanlash endi **409 bermaydi** (avvalgi
   `ConflictError("Siz allaqachon shu tarifdasiz")` olib tashlandi) —
   bu ataylab qilingan xulq-atvor o'zgarishi. Muddati o'tgan tarif
   **lazy-expiry** bilan aniqlanadi (`get_my_plan()`da hisoblanadi, DB
   yozuvi o'zgarmaydi, cron/scheduled job shart emas — frontend ham
   shunday qiladi). `Plan.listing_limit` qo'shildi (bepul:1, standart:3,
   biznes:7, premium:15 — bu raqamlar katalog matnida allaqachon bor
   edi) — **faqat ma'lumot sifatida**, kuchga kiritish (limitdan
   oshgan e'lonlarni pauza qilish) qo'shilmadi, chunki frontendda ham
   hali faqat ogohlantiruvchi matn, dasturiy ravishda amalga
   oshirilmagan.
2. **`Listing`ga yangi `Aqua` turi** (basseyn/sauna/akvapark) va
   **`old_price`** ustuni (Tour'dagi mavjud naqshga mos — chizib
   ko'rsatiladigan eski narx). `atm_banks`/`nearby_exchanges` (yangi
   Hotel/Sanatorium maydonlari) va Dining'ning yangi qoida maydonlari —
   **hech qanday backend o'zgarishi kerak bo'lmadi**, allaqachon ochiq
   `Listing.extra: JSONB`ga to'g'ridan-to'g'ri sig'adi.
3. **Qidiruv filtri kengaytmalari**: `tours.search()`ga `max_price`/
   `discount_only`, `operators.search()`ga `min_rating` — mavjud
   ustunlarga asoslangan oddiy filtrlar. `month`/`scope`/`with_tours_only`/
   `experience` kabi `extra` JSONB ichini qidirishni talab qiladigan
   filtrlar **keyingi bosqichga qoldirildi** (frontend hali real
   API'ga ulanmagani uchun hozircha shoshilinch emas).

Doiradan tashqari qoldirilgan (tadqiqot bilan asoslangan): Wallet,
to'lov usullari, `landmarks.ts`/`distances.ts` (client tomonda
hisoblanadi), `OperatorReviews.tsx` (to'liq frontend-mock,
`reviews` moduli qamrovi o'zgarmaydi), `TourOperator`ning yangi
`bizForm`/`legalAddress`/`legalDistrict` maydonlari (faqat GID
profiliga tegishli, `operators` moduli doirasidan tashqarida).

Test soni: 186 (hammasi o'tdi). Spec: `docs/superpowers/specs/2026-08-03-frontend-sync-plans-listings-search.md`.
Chat moduli va bu ish **commit qilingan va GitHub'ga push qilingan**
(2026-08-03, 4 ta commit: docs+chat, docs+sync).

Foydalanuvchi bilan kelishilgan: **frontend'ni real API'ga ulashdan
oldin qolgan barcha backend qismlari to'liq tugatiladi.** Bu shart
bajarildi — shu sessiyada frontend integratsiyasi boshlandi (pastga
qarang).

### Frontend integratsiyasi — Auth/Login/Register oqimi (2026-08-03)

Backend'ning barcha modullari tayyor bo'lgach, foydalanuvchi
frontend'ni (`front0308`) haqiqiy API'ga ulashni so'radi, **auth/login/
register oqimidan boshlab**. Tadqiqot shuni ko'rsatdi: frontend hozirgacha
**to'liq parolsiz** edi — "SMS OTP" butunlay client-tomonda simulyatsiya
qilingan (`Math.random()` kod, foydalanuvchining o'ziga ko'rsatilgan,
haqiqiy SMS yo'q), "login qilingan" holat esa faqat `currentUserId`
— token/JWT tushunchasi umuman yo'q edi. Foydalanuvchi bilan
kelishildi: **parol asosida auth** (OTP emas) va **localStorage**da
token saqlash.

**Backend qo'shimchasi**: `POST /api/v1/auth/refresh` (yangi) —
oldin `refresh_token` yaratilardi-yu, uni ishlatadigan endpoint yo'q
edi (`access_token` 30 daqiqada tugaydi — refresh'siz foydalanuvchi
har 30 daqiqada kutilmaganda chiqib qolardi). `decode_token`/
`service.get_by_id`/`service.issue_tokens` — mavjud, qayta ishlatildi.
`UserOut`ga `biz_category` qo'shildi (ro'yxatdan o'tishda yig'ilardi,
lekin hech qachon qaytarilmasdi). 10 ta test qo'shildi
(`tests/test_users.py` — birinchi marta yaratildi, ilgari auth uchun
alohida test fayli yo'q edi).

**Frontend (`front0308`) o'zgarishlari**:
- Yangi `src/lib/apiClient.ts` — fetch o'ramasi, backend'ning ikki xil
  xato shaklini (`{"detail": "matn"}` va `{"detail": [{"msg":...}]}`)
  ham qamraydi.
- `src/store/auth.ts` — `accessToken`/`refreshToken` qo'shildi,
  `login`/`register` endi **async**, haqiqiy backend'ga so'rov
  yuboradi, `hydrateSession()` (yangi) — ilova ochilganda tokenni
  tekshiradi, 401 kelsa bir marta refresh qiladi. **Muhim arxitektura
  qarori**: `users: Record<string, User>` mock-do'kon SHAKLI saqlanib
  qoldi (`useCurrentUser()` — 39 ta iste'molchi fayl uchun yagona
  kirish nuqtasi, unga tegilmadi) — `register`/`login` haqiqiy backend
  javobini shu dict'ga real UUID kaliti bilan **merge** qiladi
  (overwrite emas — `favorites`/`bizTypes`/`planUntil` kabi hali
  backend'da yo'q maydonlar saqlanib qoladi). Bu bilan hamyon/bron/
  sevimlilar kabi hali mock quyi tizimlar hech qanday o'zgarishsiz
  ishlashda davom etadi — ular alohida navbatda ulanadi.
- `OtpStep.tsx` **o'chirildi** (endi hech qayerda ishlatilmaydi) —
  ichidagi routing mantig'i (rol asosida `/host`/`/dashboard`/`/admin`,
  wizard-ochish so'rovlari, `bizTypeAfter` holati) `RegisterForm.tsx`/
  `LoginForm.tsx`ga ko'chirildi. Demo-login tugmalari (`CLIENT-01`/
  `OWN-441`, SMS'siz) olib tashlandi — haqiqiy backend'da bu ID'lar yo'q.
- `SessionGuard.tsx` — eski `validateSession(deviceId)` (soxta qurilma-
  ishonch tekshiruvi) o'rniga `hydrateSession()` chaqiradi.
- `sessions`/`DeviceSession`/`rememberDevice`/`revokeSession` — **saqlanib
  qoldi** (o'chirilmadi) — `DeviceSessions.tsx` (akkaunt sozlamalari,
  hali dekorativ) hamon ulardan foydalanadi, faqat endi real auth
  gate'iga ta'sir qilmaydi.
- **Doiradan tashqari** (keyingi navbatda): wallet/bookings/reviews/
  favorites/plans hamon mock; `bizTypes`/`planUntil`/`planPeriod`/
  `planRate`/`joinDate`/`birthDate` backend'da bor lekin bu bosqichda
  frontend `User`ga ulanmagan; boshqa foydalanuvchi ma'lumotini
  ko'rsatish (host ismi, chat sherigi) — umumiy "ID bo'yicha user olish"
  endpoint yo'q va qo'shilmadi.

**Tekshirish**: TypeScript (`tsc --noEmit`) toza, ESLint toza, frontend
test to'plami 355/355 o'tdi (`auth.test.ts` yangi async imzoga
moslashtirildi, `fetch` mock qilingan). Backend orqali to'liq
register→me→refresh→me oqimi va CORS (`localhost:3000` uchun) curl
bilan tasdiqlandi. **Muhim cheklov**: bu sessiyada haqiqiy brauzer
avtomatlashtirish vositasi (Playwright/MCP) mavjud emas edi — UI orqali
qo'lda bosib ko'rish (ro'yxatdan o'tish/kirish tugmalarini bosish)
qilinmadi, faqat backend'ga aynan frontend yuboradigan so'rovlarni
takrorlash orqali tasdiqlandi. **Keyingi sessiya (yoki foydalanuvchi
o'zi) buni brauzerda qo'lda tekshirishi tavsiya etiladi.**

Spec/reja fayli: `/Users/a1111/.claude/plans/unified-wondering-prism.md`
(vaqtinchalik). Commit qilinmagan hali (backend: `users/router.py`,
`users/schemas.py`, `tests/test_users.py`; frontend: alohida repo,
`front0308/damber-front`, hali commit qilinmagan).

**Keyingi sessiya shu yerdan boshlanishi kerak**:
- Auth integratsiyasini brauzerda qo'lda tekshirish (ro'yxatdan o'tish,
  kirish, sahifani yangilash — sessiya saqlanishi)
- Ikkala repo'da commit + push (backend va frontend alohida)
- Keyingi modulni ulash — tavsiya: **Wallet** (eng sodda, boshqa ko'p
  narsa unga bog'liq) yoki **Listings** (qidiruv/e'lon — eng ko'rinadigan)

## Agent skills

### Issue tracker

Issues live in GitHub Issues (`daminov96/damber-backend`), via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
