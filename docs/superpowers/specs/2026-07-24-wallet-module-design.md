# Wallet moduli — dizayn

**Sana**: 2026-07-24
**Holat**: Tasdiqlangan

## Kontekst

Frontend'da (`src/store/auth.ts`) wallet mantig'i `User` obyekti ichida yashaydi: `walletBalance`, va `WalletTx` tarixi (`topup`, `pay`, `payFromWallet`, `logWalletTx` amallari). Backend'da `User.wallet_balance` ustuni allaqachon mavjud (`app/modules/users/models.py`). Bu spec — balans harakati tarixini (`wallet_transactions`) va topup/pay/transfer amallarini backend'da to'liq amalga oshiradi.

Bookings moduli (keyingi spec) escrow uchun `transfer()` funksiyasini ichki chaqiruv sifatida ishlatadi — shu sabab bu spec Wallet'ni Bookings'dan oldin qamrab oladi.

## Ma'lumotlar modeli

`app/modules/wallet/models.py`:

```python
class WalletTxKind(enum.StrEnum):
    topup = "topup"
    promo = "promo"
    booking = "booking"
    refund = "refund"
    other = "other"

class WalletTxStatus(enum.StrEnum):
    success = "success"
    pending = "pending"

class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    id: UUID (pk)
    user_id: UUID (FK users.id, index)
    label: str
    amount: Numeric(14,2)  # musbat = kredit, manfiy = debit
    status: Enum(WalletTxStatus)
    kind: Enum(WalletTxKind) | None
    method: str | None       # masalan "Uzcard", "Humo" (hozircha faqat qo'lda kiritilgan yorliq)
    ref: str | None          # bog'liq booking/listing id
    created_at: datetime
```

`users.wallet_balance` — **source of truth**. `wallet_transactions` faqat tarix/journal. Balans hech qachon tranzaksiyalar yig'indisidan qayta hisoblanmaydi (hozirgi bosqich uchun ortiqcha murakkablik).

## Endpoints

Prefix `/api/v1/wallet`, barchasi `CurrentUser` bilan himoyalangan:

| Method | Path | Tavsif |
|---|---|---|
| GET | `/wallet/balance` | `{balance: float}` |
| GET | `/wallet/transactions` | Pagination bilan tarix (eng yangi birinchi) |
| POST | `/wallet/topup` | `{amount, method?}` — balansni oshiradi, `kind=topup, status=success` tranzaksiya yozadi |

**`transfer()` va `pay()` uchun public endpoint yo'q** — bu funksiyalar faqat boshqa modullar (Bookings) tomonidan service-darajasida ichki chaqiriladi. Foydalanuvchi to'g'ridan-to'g'ri boshqa userga pul o'tkaza olmaydi.

## Service funksiyalari (`app/modules/wallet/service.py`)

- `get_balance(user) -> float`
- `list_transactions(db, user, page, page_size) -> tuple[list[WalletTransaction], int]`
- `topup(db, user, amount, method=None) -> WalletTransaction`
- `pay(db, user, amount, label, kind=WalletTxKind.other, ref=None) -> WalletTransaction` — balans yetarli bo'lmasa `ConflictError`; aks holda balansni kamaytiradi va manfiy summali tranzaksiya yozadi
- `transfer(db, from_user, to_user, amount, label, kind=WalletTxKind.other, ref=None) -> tuple[WalletTransaction, WalletTransaction]` — ikki tomonlama: `from_user`dan debit, `to_user`ga kredit, ikkita tranzaksiya yozuvi. **Faqat ichki chaqiruv uchun** (Bookings service import qilib chaqiradi)

**Race condition himoyasi**: balansni o'qish/yangilashda `SELECT ... FOR UPDATE` (`with_for_update()`) ishlatiladi — bir vaqtda kelgan ikki so'rov balansni noto'g'ri hisoblamasligi uchun.

## Validatsiya

- `amount > 0` barcha amallarda (Pydantic `Field(gt=0)`)
- `pay`/`transfer`da balans yetarli bo'lmasa `ConflictError` ("Balansda mablag' yetarli emas")

## Test strategiyasi

Mavjud `tests/conftest.py` fixture'laridan foydalaniladi. Qamrov:
1. Topup balansni oshiradi va tranzaksiya yaratadi
2. Balans va tranzaksiya tarixini o'qish (`GET /wallet/balance`, `GET /wallet/transactions`)
3. `pay()` — yetarli balansda muvaffaqiyatli, tranzaksiya yoziladi
4. `pay()` — yetarsiz balansda `ConflictError` (409), balans o'zgarmaydi
5. `transfer()` — ikkala user balansi to'g'ri yangilanadi, ikkita tranzaksiya yoziladi (servis-darajasida to'g'ridan-to'g'ri chaqirib sinaladi, chunki public endpoint yo'q)

## Migratsiya

`alembic revision --autogenerate -m "wallet_transactions jadvali"`, oldindan `migrations/env.py`ga `app.modules.wallet.models` importi qo'shiladi.

## Doiradan tashqari (keyingi speclar)

- Haqiqiy to'lov gateway integratsiyasi (Click/Payme) — hozircha topup "qo'lda" (darhol muvaffaqiyatli)
- Bookings moduli (escrow, `transfer()`ni ichki chaqiradi)
- Public wallet-to-wallet transfer (agar kelajakda kerak bo'lsa)
