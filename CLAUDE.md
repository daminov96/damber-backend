## Loyiha holati (2026-08-06)

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
  Commit qilingan va GitHub'ga push qilingan (2026-08-03).

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
bilan tasdiqlandi. **Foydalanuvchi o'zi brauzerda sinab ko'rgan va
tasdiqlagan** — real ro'yxatdan o'tish Postgres'da ko'rindi (`Daminov
Jonibek`, `998504777060`).

Backend: commit qilingan va push qilingan (`099841e`). Frontend:
commit qilingan va push qilingan (`8954672`; `front0308` repo'sida
370+ ta boshqa commit qilinmagan fayl ham bor — ularga tegilmadi,
faqat auth uchun o'zgartirilgan 7 ta fayl alohida commit qilindi).

### Frontend integratsiyasi — Wallet (2026-08-03, xuddi shu sessiya)

Auth'dan keyingi navbatdagi modul — foydalanuvchi bilan kelishilgan
(3 variantdan: Wallet/Listings/Plans → Wallet tanlandi). **Backend
o'zgarishi kerak bo'lmadi** — `GET /wallet/balance`, `GET /wallet/
transactions`, `POST /wallet/topup` allaqachon frontend ehtiyojiga
mos edi (`pay`/`credit`/`transfer` ataylab faqat ichki, public
endpoint yo'q — bu Wallet integratsiyasining tabiiy chegarasini
belgiladi: balans/to'ldirish/tarix real, "to'lov" funksiyalari
(bron avansi, tarif sotib olish) hali mock — ular alohida navbatda).

Frontend: `WalletTxKind`ga `"plan"` qo'shildi (backend'da bor edi,
frontend yo'q — `WalletJournal.tsx`dagi `KIND_META` bilan birga).
`auth.ts`ga `fetchWalletTransactions()`/`topupWallet()` (yangi, real
backend'ga ulangan) — **mavjud** `topup()`/`pay()`/`logWalletTx()`
funksiyalariga **tegilmadi** (ular `HostPlansTab.tsx`ning hali mock
tarif-almashtirish oqimida ishlatiladi, bu safar doiradan tashqarida).
`WalletJournal.tsx` — `useEffect` orqali mount'da haqiqiy tarixni
so'raydi (host va dashboard ikkalasida ham ishlaydi, chunki komponent
umumiy). `TopupModal.tsx::onGatewaySuccess` — endi real
`POST /wallet/topup`ga so'rov yuboradi, xato holatini ko'rsatadi.

TypeScript/ESLint toza, 355/355 test o'tdi (regressiyasiz). Curl
bilan to'liq oqim tasdiqlandi: balans/to'ldirish/tarix, va `"plan"`
turi (tarif sotib olish tranzaksiyasi) to'g'ri ko'rinishi ham
tekshirildi. Commit qilingan va push qilingan (`b6dd743`).

### Frontend integratsiyasi — Plans (2026-08-03, xuddi shu sessiya)

Foydalanuvchi "ikkalasini ham" (Listings + Plans) so'radi. Listings
uchun chuqur tadqiqot o'tkazildi va **ancha katta ekanligi aniqlandi**
(quyida "Listings — doiradan tashqari qoldirildi" bo'limiga qarang) —
foydalanuvchi bilan kelishilgan holda **faqat Plans shu sessiyada
ulandi**, Listings alohida rejalashtirish talab qiladi.

**Backend o'zgarishi kerak bo'lmadi** — `GET /plans`, `GET /plans/mine`,
`POST /plans/switch` allaqachon frontend ehtiyojiga mos edi.

Tadqiqot muhim narsani topdi: frontend'da tarif muddati/kunlar-qoldi
hisobi **3 joyda mustaqil takrorlangan edi** (`HostPlansTab.tsx`,
`app/host/page.tsx` yon paneli, va bevosita `user.planUntil`/
`planRate` maydonlaridan) — bu ikkala joy ham endi bitta manbadan
(`myPlan`, `GET /plans/mine` javobi) o'qiydi, mustaqil
`daysUntilFrom()` chaqirmaydi.

Frontend: `auth.ts`ga `plansCatalog`/`myPlan` state va
`fetchPlansCatalog()`/`fetchMyPlan()`/`switchPlan()` (yangi) qo'shildi.
`HostPlansTab.tsx`: `getPlans()` (statik) → real `plansCatalog`;
mijoz-tomon `planQuote()` hisobi **preview sifatida saqlanib qoldi**
(tasdiqlash oynasida darhol ko'rsatish uchun, tarmoq so'rovisiz), lekin
haqiqiy summani backend `POST /plans/switch` hisoblaydi va yechadi —
`confirm()` endi `switchPlan()` chaqiradi, muvaffaqiyat xabari
backend'dan qaytgan HAQIQIY `plan_until`dan yoziladi (preview'dan
emas). `app/host/page.tsx`: yon paneldagi "Tarif" kartochkasi endi
`myPlan`dan (bir marta sahifa mount'ida so'raladi).

TypeScript/ESLint toza, 355/355 test o'tdi. Curl bilan to'liq oqim
tasdiqlandi: katalog/mening tarifim/almashtirish — barcha maydonlar
(`listing_limit`/`badge`/`emblem`/`plan_rate`/`days_left`) frontend
kutgan shaklga aynan mos keldi. Commit qilingan va push qilingan
(`0a60fcf`).

### Listings — doiradan tashqari qoldirildi (tadqiqot bilan asoslangan)

Chuqur tadqiqot shuni ko'rsatdi: Listings integratsiyasi Wallet/Plans'dan
sifat jihatidan boshqacha — bir nechta **haqiqiy arxitektura qarori**
talab qiladi, oddiy "ulash" emas:
1. **Amenities enum'i**: frontendda 90 ta qiymat, backend'da ~11 ta —
   backend enum'ini sezilarli kengaytirish kerak.
2. **~45 ta maydon** (xona turlari, sanatoriy/dining maxsus maydonlari,
   promo/qoidalar) backend'ning `extra` JSONB'siga moslashtirilishi
   kerak — bu alohida dizayn ishi.
3. **Rasm yuklash arxitekturasi boshqacha**: frontend `data:` URL
   (base64) saqlaydi, backend haqiqiy `multipart/form-data` kutadi —
   wizard'ni qayta qurish kerak (`File` obyektlarini saqlab qolish).
4. **Sahifalash (pagination) umuman yo'q** — qidiruv butun ro'yxatni
   bir vaqtda ko'rsatadi.
5. **Rad etish (reject) UI'si umuman yo'q** — backend'da bor
   (`rejected`/`reject_reason`), frontendda mutlaqo qurilmagan.
6. Video/menyu-PDF/litsenziya fayli yuklash — backend'da hech qanday
   endpoint yo'q.
7. Ikki alohida manba (`src/data/listings.ts` statik massiv +
   `myListings.ts` localStorage do'koni) bitta haqiqiy backend'ga
   birlashtirilishi kerak; `app/listing/[id]/page.tsx`ning
   `generateStaticParams()` (build-vaqtida statik sahifalar) dinamik
   render'ga o'zgartirilishi kerak.

Bu ish **alohida sessiya/reja talab qiladi** — shu sessiyada
boshlanmadi.

Frontend'dagi Auth+Wallet+Plans ishlari `main` branch'ga commit
qilingan **va GitHub'ga push qilingan** (2026-08-03).

### Listings — Bosqich 0+1 amalga oshirildi (2026-08-04)

Foydalanuvchi Listings uchun batafsil (4-bosqichli) reja so'radi.
To'liq reja `/Users/a1111/.claude/plans/unified-wondering-prism.md`da
(vaqtinchalik). Kelishilgan qarorlar: fayl yuklash (video/menyu/
litsenziya) — Bosqich 2'da haqiqiy yuklash qo'shiladi (URL-only emas);
rad etilgan e'lonni tahrirlash — backend avtomatik `rejected=False`
qiladi; **shu sessiyada faqat Bosqich 0 (backend) va Bosqich 1
(qidiruv+ko'rish, faqat o'qish) amalga oshirildi**.

**Muhim tuzatilgan taxmin**: avvalgi tadqiqotda "backend'da ~11 ta
amenity" deb taxmin qilingan edi — aniq tekshiruv shuni ko'rsatdi:
**46 ta** bor edi (frontendning 90 tasidan), aniq diff 44 ta — toza,
konfliktsiz qo'shimcha (`Amenity`/`SortOption` — DB enum EMAS, faqat
Python validatsiya, **migratsiya kerak bo'lmadi**).

**Backend** (`listings/models.py`/`service.py`/`router.py`): 44 ta
yangi amenity qiymati (90 taga yetdi, frontend bilan bir xil);
`SortOption.discount`; `search()`ga `query`/`min_rating` filtri;
`get_by_id()` har chaqiriqda `views += 1`; `update()` — rad etilgan
e'lonni tahrirlash avtomatik `rejected=False` qiladi (Bosqich 2 uchun
oldindan tayyorlandi, hozircha frontend orqali foydalanilmaydi). 4 ta
yangi test, jami 200 test o'tdi. Curl bilan to'liq tekshirildi.

**Frontend — muhim rejadan chetlanish (shaffof qayd etiladi)**: reja
matnida "sahifalash (pagination) qo'shiladi" deyilgan edi, lekin
amalga oshirish paytida aniqlandiki, `SearchClient.tsx`ning mavjud
filtrlash arxitekturasi (tur plitkalari hisoblagichi, "o'xshash
takliflar", "yumshatilgan takliflar" — ~800 qatorli `searchCatalog.ts`)
**butun to'plamga** asoslangan — chinakam cursor-based sahifalash shu
arxitekturaning katta qismini qayta qurishni talab qilardi. Buning
o'rniga: `SearchClient.tsx` endi real backend'dan **bitta so'rovda
kattaroq to'plam** oladi (`SEARCH_POOL_SIZE=100`, `useEffect` orqali),
mavjud client-tomon filtrlash (`filterStays` va h.k.) **o'zgarishsiz**
shu haqiqiy ma'lumot ustida ishlaydi. Bu — hozirgi e'lonlar soni uchun
to'g'ri va halol yechim (mock emas, real Postgres'dan), lekin **haqiqiy
sahifalash hali yo'q** — e'lonlar soni ko'payganda alohida ish sifatida
qo'shilishi kerak. Bu qaror hujjatda (`SearchClient.tsx` sharhida ham)
qayd etilgan.

- `src/lib/listingsAdapter.ts` (yangi) — `mapBackendListing()` (`extra`
  JSONB'dan ~40 ta frontend maydonini tiklaydi), `buildListingSearchParams()`.
- `src/lib/api.ts` — YANGI funksiyalar qo'shildi (`searchListingsReal()`,
  `fetchListingById()`) — **mavjud** `getListings()`/`getListing()`/
  `getHotListings()`/`getMostSaved()` **o'zgarishsiz qoldirildi** (bular
  20 dan ortiq boshqa faylda ishlatiladi — homepage, admin statistika,
  chat, bron kalendari va h.k. — Bosqich 1 doirasi faqat qidiruv+ko'rish
  bo'lgani uchun ularga tegilmadi, keyingi navbatda o'z-o'zidan ulanadi).
- `app/listing/[id]/page.tsx` — `generateStaticParams()` olib
  tashlandi (`dynamic = "force-dynamic"`), real `fetchListingById()`
  chaqiradi; topilmasa hali mock `MyListingDetail` fallback (Bosqich
  2'gacha saqlanadi).

TypeScript/ESLint toza, 355/355 test o'tdi (regressiyasiz). Brauzer/curl
orqali tekshirildi: real e'lon yaratilib, `/listing/{real-uuid}`
sahifasi server-tomonda uni to'g'ri render qilishi va har yuklanishda
`views` oshishi tasdiqlandi. Commit qilinmagan hali (backend va frontend
ikkalasida).

### Listings — Bosqich 2 amalga oshirildi (2026-08-04, xuddi shu sessiya)

Xost CRUD (yaratish/tahrirlash/o'chirish/to'xtatish) va rasm/video/menyu/
litsenziya fayl yuklash — real backend'ga ulandi.

**Backend**: `listings.video_url`/`license_doc_url` ustunlari (migratsiya
`66ee07f668c0`), `POST /listings/{id}/upload-file` (`field: video|menu|
license`, kontent-turi va hajm cheklovi field'ga qarab) — javob `{url}`,
Listing'ning o'zini o'zgartirmaydi (bitta mas'uliyat). 3 ta yangi test,
jami 203 test o'tdi. Curl bilan to'liq oqim tekshirildi (yaratish → rasm
multipart yuklash → video upload-file → PATCH → `/mine` → pause/unpause →
delete).

**Frontend — asosiy dizayn qarori**: `listingsAdapter.ts::buildListingPayload()`
— WizardStepPrice HAR DOIM to'liq `NewListingInput` quradi (qisman patch
emas), shuning uchun bitta builder ham create, ham update uchun ishlatiladi.
`TOP_LEVEL_KEYS` ro'yxatida yo'q har qanday maydon avtomatik `extra`ga
tushadi — yangi wizard maydoni qo'shilsa bu ro'yxatni yangilash shart emas.
`myListings.ts::updateListing()` — patch'dagi `undefined` kalitlarni
tashlab, `current + cleanPatch`dan **to'liq obyekt qayta quradi**, keyin
shu to'liqni yuboradi — sabab: backend PATCH `extra`ni wholesale
almashtiradi (`exclude_unset` faqat top-level maydonlar uchun ishlaydi),
qisman yuborilsa boshqa `extra` kalitlari (masalan `promo`) yo'qolib
qolardi.

**Media yuklash orqali**: rasmlar/video/menyu/litsenziya wizard'da hamon
`data:` dataURL sifatida saqlanadi (mavjud siqish/preview pipeline'iga
tegilmadi) — submit vaqtida `myListings.ts::attachMedia()` ularni
`fetch(dataURL).blob()` orqali haqiqiy Blob'ga aylantirib yuklaydi
(rasmlar — `/photos` multipart, video/menyu/litsenziya — `/upload-file`),
so'ng natijaviy URL'larni yakuniy PATCH bilan biriktiradi. Video/menyu —
`videoFileUrl`/`menuFileUrl` (fayl) tashqi havola maydonidan (`videoUrl`/
`menuUrl`) ustuvor — xuddi shu naqsh ikkalasida ham. Litsenziya hujjati
va menyu PDF avval **butunlay soxta edi** (faqat fayl nomi saqlanardi,
mazmuni hech qayerda yo'q edi) — foydalanuvchi "haqiqiy yuklash" deb
so'ragani uchun `WizardStepInfo.tsx`/`WizardStepMedia.tsx`ga video bilan
bir xil FileReader→dataURL naqshi qo'shildi.

**`myListings.ts` to'liq qayta yozildi**: `persist`/localStorage olib
tashlandi (backend yagona haqiqiy manba — `fetchMine()` har safar qayta
so'raydi), `pausedStaticIds`/`removedStaticIds` yo'qoldi (statik seed +
soya-nusxa tushunchasi butunlay tugadi). `app/host/page.tsx`dagi
`myListings` — endi to'g'ridan-to'g'ri `useMyListings().items`
(`/listings/mine` allaqachon egalik bo'yicha filtrlaydi). `approve()`
mahalliy/mock qoldi (faqat `AutoModeration.tsx`ning dekorativ taymeri
uchun — haqiqiy tasdiqlash admin panelidan).

**`ListingActivation.tsx`**: `finalize()` async bo'ldi (haqiqiy
`addListing`/`updateListing` chaqiradi), muvaffaqiyatsizlikda `payError`
ko'rsatadi; pullik reklama oqimida (`payAndPublish`) agar backend
yaratish/yangilash muvaffaqiyatsiz bo'lsa — mahalliy (mock) hamyondan
yechilgan summa **yangi `auth.ts::refund()` orqali qaytariladi**
(`pay()`ning teskarisi). `localStorage` kvota-xato ko'rsatuvchi eski
`saveIssue` bloki olib tashlandi (endi og'ir media localStorage'ga
yozilmaydi — sabab yo'qoldi).

**Shaffof qoldirilgan cheklov (kengroq ta'sir)**: `myListings.ts::items`
semantikasi o'zgardi — avval "brauzerda yaratilgan BARCHA e'lonlar mock
to'plami" edi (kimga tegishli bo'lishidan qat'iy nazar), endi
`/listings/mine` orqali **faqat joriy foydalanuvchining o'zi** (va faqat
`fetchMine()` chaqirilgan joyda, ya'ni `/host`da). Bu quyidagilarga
ta'sir qiladi (barchasi allaqachon boshqa sabablarga ko'ra dekorativ/mock
deb hujjatlashtirilgan yoki Bookings hali ulanmagani uchun edge-case):
`AdminModerationQueue.tsx`/`AdminModerationStats.tsx`/`AdminTraffic.tsx`/
`app/admin/page.tsx` (admin — global "barcha e'lonlar" ko'rinishi endi
yo'q, faqat `seedListings`), `app/dashboard/page.tsx`ning `lookupListing`
fallback'i va `tripItems.ts` (turist rejasidagi host e'lonlari — Bookings
hali mock bo'lgani uchun bu deyarli hech qachon ishlamas edi allaqachon).
Bu fayllarga tegilmadi — real admin/tourist-cross-lookup ulash alohida
ish (Bookings integratsiyasi bilan birga hal qilinishi mantiqiy).

TypeScript/ESLint toza, 355/355 test o'tdi. Curl bilan backend tomoni
to'liq tekshirildi (yuqorida). Brauzer orqali qo'lda UI tekshiruvi
QILINMADI (bu sessiyada Playwright/brauzer avtomatlashtirish vositasi
yo'q edi) — keyingi sessiyada birinchi ish sifatida host kabinetida
haqiqiy e'lon yaratish/tahrirlash/rasm-video-litsenziya yuklash/
o'chirish/to'xtatish oqimini brauzerda qo'lda sinab ko'rish tavsiya
etiladi.

Backend: commit qilingan va push qilingan (`6183a4c`). Frontend: commit
qilingan va push qilingan (`85c66bf` — bu commit'da avvalgi
sessiyalardan qolgan, hali commit qilinmagan katta hajmdagi frontend
o'zgarishlar ham bor edi, masalan `WizardStepAmenities.tsx`ning 1821
qatorlik diff'i — CLAUDE.md tarixida hujjatlashtirilgan, foydalanuvchi
bilan aniq kelishilgan holda birga commit qilindi).

### Listings — Bosqich 3 amalga oshirildi (2026-08-06)

Rad etish/moderatsiya UI — backend allaqachon `rejected`/`reject_reason`
ni `ListingOut`da qaytarardi (Bosqich 0'dan beri), lekin frontend bu
maydonlarni umuman o'qimasdi. **Backend o'zgarishi kerak bo'lmadi.**

Frontend: `Listing`ga `rejected?: boolean`/`rejectReason?: string`
qo'shildi (`listingsAdapter.ts::mapBackendListing()` orqali to'ldiriladi,
`buildListingPayload()`ning `TOP_LEVEL_KEYS`iga ham qo'shildi — faqat
o'qish uchun, `extra`ga tushib qolmasin). `HostListingsTab.tsx::statusOf()`/
`tabOf()` — endi 4-holat: Faol / Moderatsiyada / **Rad etilgan** /
To'xtatilgan (ustuvorlik: to'xtatilgan > rad etilgan > faol > moderatsiyada);
rad etilgan e'londa "To'xtatish"/"TOP'ga ko'tarish" tugmalari
yashiriladi (mantiqsiz — e'lon hali chop etilmagan). `ListingManageModal.tsx`:
`isPending` endi `!verified && !rejected` (avval rad etilgan e'lon ham
noto'g'ri "Kutilmoqda" deb ko'rsatilardi); yangi maxsus blok — sabab
matni + "Tahrirlash va qayta yuborish" (backend'dagi avtomatik
unreject-on-edit'ga tayanadi, alohida "qayta yuborish" tugmasi shart
emas) + o'chirish tugmasi.

TypeScript/ESLint toza, 355/355 test o'tdi. Curl bilan to'liq oqim
tekshirildi: dev DB'da vaqtinchalik ADMIN akkaunt orqali (mavjud
foydalanuvchini `role='ADMIN'`ga to'g'ridan-to'g'ri SQL bilan
ko'tarish — dev-only) e'lon rad etildi → `GET /listings/mine` orqali
xost `rejected: true`/`reject_reason` matnini ko'rishi tasdiqlandi →
xost PATCH qilgach (`buildListingPayload()` shaklida) `rejected: false`
bo'lib qolishi tasdiqlandi. Brauzer orqali qo'lda UI tekshiruvi
QILINMADI (bu sessiyada ham Playwright yo'q edi).

### Chat moduli frontend'ga ulandi (2026-08-06, xuddi shu sessiya)

Backend allaqachon to'liq tayyor edi (2026-08-03), lekin frontend hamon
`localStorage`dagi mock `chats`/`unread` xaritasi va soxta 2s bot-javob
bilan ishlardi. Chuqur tadqiqot (Explore agent) backend/frontend
kontraktini solishtirdi va uchta haqiqiy uzilishni topdi:

1. **`ConversationSummaryOut`da rol maydoni yo'q edi** — frontend
   "Mijoz chatlari" (dashboard) va "Xost chatlari" (/host) ikkita alohida
   tabga suhbatlarni bo'lishi kerak, lekin backend javobida joriy
   foydalanuvchi shu suhbatda `client_id` yoki `owner_id` ekanini
   bildiruvchi hech narsa yo'q edi (faqat `other_user` — "boshqa
   ishtirokchi"). **Backend**: `ConversationSummary`/`ConversationSummaryOut`ga
   `is_client: bool` qo'shildi (`user.id == conversation.client_id`).
2. Xuddi shu sababdan **`listing_name` ham yo'q edi** — frontend qaysi
   e'lon haqida suhbat ekanini ko'rsatish uchun N+1 so'rov qilishga
   majbur bo'lardi. **Backend**: `listing_name: str | None` qo'shildi
   (`_build_summary()` ichida `Listing.name`dan bitta qo'shimcha
   so'rov — `other_user` bilan bir xil naqsh).
3. **Mock'dagi "bot javob" va "egasi nomidan soxta tasdiq xabari"
   (`BookingModal.tsx`) haqiqiy backend'da mutlaqo imkonsiz** — xabar
   doim JWT'dagi joriy foydalanuvchi nomidan yuboriladi, mijoz
   "egasi nomidan" xabar yubora olmaydi (xavfsizlik nuqtai nazaridan
   ham to'g'ri). Ikkalasi ham **butunlay olib tashlandi** (soxta edi,
   haqiqiy muqobili yo'q) — `BookingModal.tsx` endi faqat mijozning
   O'Z yozgan xabarini (agar bo'lsa) egasi bilan haqiqiy suhbatga
   yuboradi (`startConversation`+`sendMessage`, bron oqimini
   bloklamaydi).

**Backend**: yuqoridagi 2 ta yangi maydon (`is_client`/`listing_name`)
dan boshqa o'zgarish yo'q edi — qolgan hammasi (endpointlar, sezgir
ma'lumot filtri, `(client_id, owner_id)` juftlik identifikatsiyasi,
ishtirokchi-cheklovi) allaqachon frontend ehtiyojiga mos edi. 2 ta yangi
test, jami 206 test o'tdi.

**Frontend**: `store/chat.ts` to'liq qayta yozildi — `persist`/
localStorage, `chatIdFor` (composite `${clientId}_${ownerId}` kalit),
`botReply` olib tashlandi; endi `conversations: Conversation[]` +
`messagesByConversation: Record<uuid, Message[]>`, real `id`lar,
to'liq ISO timestamp, **xabar darajasidagi** `read_at` (avval bitta
thread-darajasidagi boolean edi). `detectSensitiveData()` mijoz-tomon
tezkor tekshiruv sifatida saqlanib qoldi (darhol xabar berish uchun),
lekin server 400'i ham alohida ko'rsatiladi (ikkala regex bir xil emas —
server biroz kengroq). `ChatThread.tsx` — websocket yo'qligi sababli
oddiy 5s polling (`setInterval`) + thread ochilganda avtomatik
`markRead` (avval buni parent komponentlar chaqirishi kerak edi,
endi markazlashgan). `ListingChat.tsx` — `ownerId`+`chatIdFor` o'rniga
`listingId` bilan `startConversation()` chaqiradi (backend `listing_id`dan
`owner_id`ni serverda hal qiladi va o'z-e'loniga-yozish tekshiruvini
serverda bajaradi — 409); UI darajasidagi tezkor tekshiruv (`user.id
=== ownerId`) tarmoq so'rovisiz saqlanib qoldi. `ClientChats.tsx`/
`HostChats.tsx` — `cid.split("_")` orqali taxminiy egasi/mijoz
aniqlash o'rniga `is_client`/`other_user` (backend haqiqiy hal qiladi)
ishlatadi; "qaysi e'lon haqida" endi taxmin emas, haqiqiy
`listingName`. `app/host/page.tsx`/`app/dashboard/page.tsx` badge
hisoblagichlari — mock xaritalarni parse qilish o'rniga
`conversations`/`unreadCount`dan.

TypeScript/ESLint toza, 358/358 test o'tdi (yangi `chat.test.ts` —
`vi.stubGlobal("fetch")` naqshi, `auth.test.ts`ga o'xshab). Curl bilan
to'liq oqim tekshirildi: mijoz suhbat boshlaydi → xost o'z e'loniga
yozishga urinsa 409 → mijoz xabar yuboradi → sezgir ma'lumot 400 →
xost ro'yxatida `is_client: false` ko'rinadi → xost javob beradi →
mijozda `unread_count: 1` → `markRead` → `unread_count: 0` → begona
foydalanuvchi 403 oladi. Brauzer orqali qo'lda UI tekshiruvi QILINMADI
(bu sessiyada ham Playwright yo'q edi).

**Keyingi sessiya shu yerdan boshlanishi kerak**:
- Listings Bosqich 2+3 va Chat modulini brauzerda qo'lda sinash (hali
  birortasi ham qilinmagan)
- Haqiqiy cursor-based sahifalash (`SearchClient.tsx`) — e'lonlar soni
  ko'payganda
- `NotificationBell.tsx` chat store'ga ulanmagan (faqat bron
  bildirishnomalarini ko'rsatadi) — real chat unread'ni navbar
  qo'ng'irog'iga qo'shish alohida ish
- Bookings moduli hamon to'liq mock (backend tayyor, frontend ulanmagan)
- Admin panel (`AdminModerationQueue`/`AdminTraffic`/`app/admin/page.tsx`)
  hamon `seedListings` + user-scoped `useMyListings` bilan ishlaydi,
  global "barcha e'lonlar" ko'rinishi yo'q (Bosqich 2 eslatmasiga qarang)
  — real admin-wide listing endpoint'ga ulash alohida ish

## Agent skills

### Issue tracker

Issues live in GitHub Issues (`daminov96/damber-backend`), via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
