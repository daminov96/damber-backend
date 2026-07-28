## Loyiha holati (2026-07-28)

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
  Hali commit qilinmagan.

**Keyingi sessiya shu yerdan boshlanishi kerak**: Operators o'zgarishlarini
ko'rib chiqib commit qilish (foydalanuvchi so'rasa), so'ng **`tours`**
moduliga o'tish (operator profiliga bog'langan turlar; `TourBooking`
oddiy so'rov/lead-capture sifatida quriladi — to'lov/eskrov YO'Q,
chunki frontendda ham yo'q, foydalanuvchi bilan shunday kelishilgan).
Undan keyin **`rent_companies`** (yengil profil-wrapper, `listings`ga
`company_id` FK qo'shiladi, RentCar bronlari mavjud `bookings`
oqimidan foydalanadi — o'zgarishsiz).

Keyingi bosqichlar (Tours/RentCompanies'dan keyin, alohida speclar):
- Frontend'ni haqiqiy API'ga ulash (`src/lib/api.ts`ni yangilash)
- JWT saqlash strategiyasi frontend tomonida (localStorage vs cookie)
- Reviews, Chat, Admin (to'liq), Plans, Gid (guide) profillari

## Agent skills

### Issue tracker

Issues live in GitHub Issues (`daminov96/damber-backend`), via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
