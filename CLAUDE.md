## Loyiha holati (2026-07-24)

Backend qurilishi bosqichma-bosqich davom etmoqda. Frontend manbasi:
`D:\projects\dam\front\last\damber-front` (Next.js, hozircha to'liq
localStorage-mock, haqiqiy API chaqiruvi yo'q — `src/lib/api.ts` va
Zustand store'lar backend contract'ini belgilaydi).

**Tayyor modullar:**
- `users` — register/login/me, JWT, rollar (B2C/B2B/ADMIN)
- `listings` — CRUD, qidiruv/filtr, rasm yuklash (LocalDiskStorage),
  ADMIN moderatsiyasi. Spec: `docs/superpowers/specs/2026-07-24-listings-module-design.md`
- `wallet` — balans (users.wallet_balance source of truth), topup,
  tarix, `pay()`/`transfer()` (faqat ichki chaqiruv uchun, public
  endpoint yo'q). Spec: `docs/superpowers/specs/2026-07-24-wallet-module-design.md`

**Navbatda: Bookings moduli** (escrow, cancellation policy, refund) —
frontend'dagi eng murakkab qism (`src/lib/refund.ts`: 15% avans,
4 ta cancellation tier — flexible/moderate/strict/nonref).

Brainstorming boshlangan, ikkita savol ochiq qoldi (foydalanuvchi
javob berishdan oldin ishni to'xtatishni so'radi):

1. **Avans to'lovi**: booking yaratilganda mehmon 15% avansni FAQAT
   wallet orqali to'laydimi (agar balans yetmasa 409, boshqa yo'l yo'q),
   yoki wallet/"keyinroq to'lash" ikkalasi ham qo'llab-quvvatlanishi kerakmi?
   Tavsiya: faqat wallet (soddaroq, Click/Payme keyingi bosqich).
2. **Cancellation policy manbai**: booking yaratilganda listing.extra
   ichidan o'qib bookingga nusxalanadimi (keyin listing o'zgarsa ham
   booking siyosati o'zgarmasin), yoki boshqa yondashuv kerakmi?
   Tavsiya: listing.extra'dan o'qib nusxalash.

**Keyingi sessiya shu yerdan boshlanishi kerak**: foydalanuvchidan
yuqoridagi ikkita savolga javob olib, keyin brainstorming/dizayn
jarayonini (`docs/superpowers/specs/`ga yozib) davom ettirish, so'ng
EnterPlanMode orqali amalga oshirish rejasi tuzish — `listings`/`wallet`
modullarida qo'llanilgan xuddi shu jarayon (spec → plan → implement →
migratsiya → test → lint → curl smoke-test → commit).

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
