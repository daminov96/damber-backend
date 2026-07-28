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
  60 test o'tdi, curl bilan to'liq oqim (quote→create→confirm→complete
  va reject→restore) tasdiqlandi. Hali commit qilinmagan.

**Keyingi sessiya shu yerdan boshlanishi kerak**: Bookings o'zgarishlarini
ko'rib chiqib commit qilish (foydalanuvchi so'rasa), so'ng quyidagi
ro'yxatdan keyingi bosqichni tanlash.

Keyingi bosqichlar (Bookings'dan keyin, alohida speclar):
- Frontend'ni haqiqiy API'ga ulash (`src/lib/api.ts`ni yangilash)
- JWT saqlash strategiyasi frontend tomonida (localStorage vs cookie)
- Tours/Operators/RentCompanies, Reviews, Chat, Admin (to'liq), Plans

## Agent skills

### Issue tracker

Issues live in GitHub Issues (`daminov96/damber-backend`), via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
