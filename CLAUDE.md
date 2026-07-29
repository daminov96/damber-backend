## Loyiha holati (2026-07-29)

Backend qurilishi bosqichma-bosqich davom etmoqda. Frontend manbasi
(lokal, rabochiy stolda): `~/Desktop/projects/damber/front/front2807/damber-front`
(Next.js, hozircha to'liq localStorage-mock, haqiqiy API chaqiruvi yo'q —
`src/lib/api.ts` va Zustand store'lar backend contract'ini belgilaydi).

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

**Rejalashtirilgan asosiy modullar ketma-ketligi tugadi**: `users` →
`listings` → `wallet` → `bookings` → `operators` → `tours` →
`rent_companies` → `guides` — barchasi tayyor, test qilingan, push
qilingan (124 test).

Foydalanuvchi bilan kelishilgan: **frontend'ni real API'ga ulashdan
oldin qolgan barcha backend qismlari to'liq tugatiladi.**

**Keyingi sessiya shu yerdan boshlanishi kerak** — quyidagilardan
birini tanlash (ustuvorlik hali kelishilmagan):
- **Reviews** — listing/tour/operator/guide uchun sharh-reyting tizimi
  (`rating`/`rating_count` maydonlari hamma joyda bor, lekin hech
  qayerda yozilmaydi — hozircha statik 0)
- **Chat** — bron/e'lon bilan bog'liq xabarlashuv (real-time/WebSocket
  talab qilishi mumkin)
- **Admin (to'liq)** — hozir faqat `approve` endpointlari bor,
  to'liq boshqaruv paneli yo'q
- **Plans** — B2B tarif rejalari (`users.current_plan_id` bor, lekin
  Plans moduli yo'q)

Shulardan keyin: **frontend'ni haqiqiy API'ga ulash** — `src/lib/api.ts`ni
localStorage-mock'dan hozirgi 8 ta backend moduliga ulash; JWT saqlash
strategiyasi (localStorage vs cookie) shu bosqichda hal qilinadi.

## Agent skills

### Issue tracker

Issues live in GitHub Issues (`daminov96/damber-backend`), via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
