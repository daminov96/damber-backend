# Admin moduli — dizayn

**Sana**: 2026-07-30
**Holat**: Taklif (foydalanuvchi tasdig'ini kutmoqda)

## Kontekst

`plans`dan keyingi bosqich — foydalanuvchi so'ragan "to'liq admin panel". Uchta parallel tadqiqot (`AdminModerationQueue`/`AdminModerationStats`, `AdminUsersControl`/`AdminTeam`/`AdminSecurity`, `AdminTraffic`/`AdminActivityLog`) shuni ko'rsatdi: frontend'dagi "Admin panel"ning katta qismi **dekorativ/soxta** — Trafik tahlili 100% qattiq kodlangan raqamlar, Xavfsizlik bo'limi asosan soxta ("Oxirgi kirishlar" jadvali statik mock), "Adminlar jamoasi" haqiqiy autentifikatsiyaga **umuman bog'lanmagan** (shu yerda yaratilgan "admin" haqiqatda tizimga kira olmaydi). Lekin bir nechta **haqiqiy** bo'shliq va **jiddiy xavfsizlik muammosi** ham topildi.

## Loyihachi qarorlar

### Xavfsizlik tuzatishi — birinchi navbatda

**Hozir `POST /auth/register` orqali istalgan kishi `role: "ADMIN"` yuborib, to'liq admin huquqi ola oladi** (`RegisterRequest.role: UserRole = UserRole.B2C` — cheklovsiz, `users/service.py::register()` buni to'g'ridan-to'g'ri ishlatadi). Bu — "to'liq admin panel" qurishning zaruriy old sharti: aks holda qurilayotgan barcha admin imkoniyatlari (moderatsiya, foydalanuvchi bloklash) ma'nosiz bo'lib qoladi, chunki ularga istalgan kishi kirisha oladi. **Tuzatiladi**: ommaviy ro'yxatdan o'tish faqat `B2C`/`B2B`ga cheklanadi; `ADMIN` hisobi faqat mavjud ADMIN tomonidan himoyalangan endpoint orqali yaratiladi.

### Nima haqiqiy, nima dekorativ — va shunga ko'ra qaror

| Frontend qismi | Holat | Qaror |
|---|---|---|
| Listing/Tour moderatsiya — tasdiqlash | Haqiqiy, backend'da bor (`approve()`) | O'zgarishsiz qoladi |
| Listing/Tour moderatsiya — **rad etish** | Haqiqiy amal, lekin **butunlay o'chirish** sifatida (status emas), sababsiz | Backend'da **soft-status** sifatida quriladi (`rejected: bool` + `reject_reason`) — o'chirish emas. Bu portlanadigan xatti-harakat emas, **ataylab yaxshilash**: loyihaning boshqa hech bir joyida "rad etish" o'chirish bilan amalga oshirilmagan (Bookings/TourBooking `rejected` statusni saqlaydi, o'chirmaydi) — Listings/Tours'da o'chirish orqali rad etish o'zi ham izchilsizlik bo'lardi. Sabab maydoni (`reject_reason`) ham qo'shiladi — frontendda yo'q edi, lekin bu haqiqiy admin ishi uchun zaruriy (Bookings'dagi `reject_reason` bilan bir xil naqsh). |
| Moderatsiya navbati (qaysi listing/tur kutmoqda) | Frontendda mahalliy do'kondan o'qiladi | **Haqiqiy backend bo'shlig'i**: hozir ADMIN uchun "kutayotgan listinglar/turlar" ro'yxatini olish endpoint'i yo'q (`listings.search()` doim faqat `verified=True`ni qaytaradi). Qo'shiladi. |
| Umumiy statistika (jami e'lon, kutayotgan, **daromad**) | Qisman haqiqiy (e'lon/kutayotgan hisoblari), lekin **"Jami daromad" — qattiq kodlangan `42500000`** | Haqiqiy hisoblash bilan almashtiriladi (`bookings`/`wallet` jadvallaridan) — frontend buni hech qachon qilmagan, lekin backend'da real ma'lumot bor. |
| Foydalanuvchi bloklash (`AdminUsersControl`) | **Haqiqiy emas** — bu aslida IP qora ro'yxati, "foydalanuvchi" ustuni faqat 3 ta qattiq kodlangan IP bilan soxta jadval. `User`da `banned`/`status` maydoni umuman yo'q. Hech qayerda kuchga kiritilmagan (login IP'ni tekshirmaydi). | **Yangi, backend-only imkoniyat sifatida quriladi** (frontend porti emas): `User.is_banned` + sabab, ADMIN ban/unban endpoint'lari, **haqiqiy kuchga kiritish** (login va har bir so'rovda tekshiriladi). Bu — "to'liq admin panel" uchun zaruriy minimal imkoniyat (aks holda admin hech kimni bloklay olmaydi). |
| "Adminlar jamoasi" (`AdminTeam`) | Dekorativ — alohida do'konda, real `useAuth.users`ga umuman yozilmaydi, "yaratilgan admin" tizimga kira olmaydi | **Haqiqiy versiyasi quriladi**: yuqoridagi xavfsizlik tuzatishi bilan bog'liq — ADMIN himoyalangan `POST /admin/users/invite-admin` orqali haqiqiy `role=ADMIN` foydalanuvchi yaratadi (parol bilan, darhol tizimga kira oladigan). Ruxsat darajalanishi (super-admin vs oddiy admin) — frontendda ham yo'q, backend ham qo'shmaydi (bitta `ADMIN` roli yetarli). |
| Xavfsizlik — 2FA, "Oxirgi kirishlar" | To'liq dekorativ/soxta (frontend o'z izohida "demo, backend bilan real bo'ladi" deb yozgan) | Qo'shilmaydi — hech qanday portlanadigan asos yo'q, alohida katta funksiya (haqiqiy 2FA/sessiya kuzatuvi). |
| Trafik tahlili (tashrif, seans vaqti, qaytish darajasi) | **100% soxta** — hatto tasodifiy emas, qattiq kodlangan konstantalar | Qo'shilmaydi — hech qanday kuzatuv infratuzilmasi (page-view/session event) loyihada yo'q, buni qo'shish butunlay yangi, so'ralmagan katta funksiya bo'lardi. |
| Faoliyat jurnali (`AdminActivityLog`) | **Haqiqiy yozish yo'li bor** (mijoz tomonida) — har bir admin amali `addLog()` chaqiradi | **Backend'da haqiqiy audit jurnali sifatida quriladi** — har bir admin amali (tasdiqlash/rad etish/bloklash/blokdan chiqarish/admin qo'shish) serverda yoziladi. Frontend naqshini (action/target/detail/vaqt) meros oladi, lekin backend'da server tomonda. |
| Qurilma/sessiya kuzatuvi (`DeviceSessions.tsx`) | Haqiqiy va ishlaydi, lekin **admin panelga aloqasi yo'q** — bu parolsiz SMS-OTP + "ishonchli qurilma" login modeliga bog'liq, hozirgi backend parol+JWT modelidan butunlay boshqacha | Doiradan tashqari — bu alohida autentifikatsiya paradigmasi, admin panelning qismi emas. |

## Ma'lumotlar modeli

**`app/modules/users/models.py`ga qo'shimcha**:
```python
is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
banned_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

**`app/modules/listings/models.py`ga qo'shimcha**:
```python
rejected: Mapped[bool] = mapped_column(Boolean, default=False)
reject_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

**`app/modules/tours/models.py`ga qo'shimcha**:
```python
rejected: Mapped[bool] = mapped_column(Boolean, default=False)
reject_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

`app/modules/admin/models.py` (yangi modul):
```python
class AuditAction(enum.StrEnum):
    listing_approve = "listing_approve"
    listing_reject = "listing_reject"
    listing_pause = "listing_pause"       # ADMIN tomonidan (mavjud toggle_pause kengaytiriladi)
    tour_approve = "tour_approve"
    tour_reject = "tour_reject"
    review_delete = "review_delete"
    user_ban = "user_ban"
    user_unban = "user_unban"
    admin_invite = "admin_invite"

class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"
    id: UUID (pk)
    admin_id: UUID (FK users.id, index)
    action: Enum(AuditAction)
    target_type: str(50)      # "listing"/"tour"/"review"/"user" — erkin, kichik yopiq to'plam
    target_id: UUID
    detail: str | None (500)
    created_at: DateTime server_default=func.now()
```

## Endpoints

### Xavfsizlik tuzatishi

`app/modules/users/schemas.py::RegisterRequest.role` — endi `Literal[UserRole.B2C, UserRole.B2B]` (yoki schema darajasida validator) — `ADMIN` qiymati ro'yxatdan o'tishda 422 bilan rad etiladi.

### `app/modules/admin/router.py` (prefix `/api/v1/admin`, barchasi `require_role(ADMIN)`)

| Method | Path | Tavsif |
|---|---|---|
| GET | `/admin/dashboard` | Umumiy statistika: userlar soni (rol bo'yicha), listinglar (jami/tasdiqlangan/kutayotgan/rad etilgan), turlar (xuddi shunday), **haqiqiy jami daromad** (bookings/wallet'dan) |
| GET | `/admin/moderation/listings` | Kutayotgan listinglar ro'yxati (sahifalab) — `listings_service`ga yangi `list_pending()` orqali |
| GET | `/admin/moderation/tours` | Kutayotgan turlar ro'yxati (sahifalab) |
| POST | `/admin/users/{user_id}/ban` | `{reason}` — `is_banned=True`, audit yoziladi |
| POST | `/admin/users/{user_id}/unban` | `is_banned=False`, audit yoziladi |
| GET | `/admin/users` | Foydalanuvchilar ro'yxati — `role`/`is_banned` filtri, qidiruv (ism/telefon), sahifalab |
| POST | `/admin/users/invite-admin` | `{name, surname, phone, password, email?}` — haqiqiy `role=ADMIN` user yaratadi, audit yoziladi |
| GET | `/admin/audit-log` | Audit jurnali — `action`/`admin_id` filtri, sahifalab |

### Mavjud modullarga qo'shimcha

- `app/modules/listings/router.py`: `POST /admin/listings/{id}/reject` (`{reason}`) — mavjud `/admin/listings/{id}/approve`ning yonida.
- `app/modules/tours/router.py`: `POST /admin/tours/{id}/reject` (`{reason}`) — xuddi shunday.
- `app/modules/listings/router.py::toggle_pause`: hozir faqat egasi — ADMIN ham qo'shiladi (`_check_owner_or_admin` qayta ishlatiladi, hozirgi bespoke `if listing.owner_id != current_user.id` tekshiruvi o'rniga) — bu ADMIN'ga tasdiqlangan listingni "yopish" (takedown) imkonini beradi.

## Service funksiyalari

`app/modules/admin/service.py`:
```python
async def log_action(db, admin, action, target_type, target_id, detail=None) -> AdminAuditLog:
    entry = AdminAuditLog(admin_id=admin.id, action=action, target_type=target_type, target_id=target_id, detail=detail)
    db.add(entry)
    await db.commit()
    return entry

async def ban_user(db, user_id, admin, reason) -> User: ...   # is_banned=True, log_action(user_ban)
async def unban_user(db, user_id, admin) -> User: ...
async def invite_admin(db, admin, payload) -> User: ...        # role=ADMIN, log_action(admin_invite)
async def get_dashboard_stats(db) -> DashboardStats: ...
async def list_audit_log(db, action, page, page_size) -> tuple[list[AdminAuditLog], int]: ...
```

**Muhim arxitektura eslatmasi**: `admin.service` — pastki qatlam moduli (`core`ga yaqin), hech qanday boshqa modulning `.service`siga bog'liq emas (faqat `.models`larga: `User`, `Listing`, `Tour`, `Booking` — statistikani hisoblash uchun `select`/`func.count`/`func.sum` bilan to'g'ridan-to'g'ri so'rov). `listings.service`/`tours.service` esa `admin.service.log_action()`ni chaqiradi (bir tomonlama bog'liqlik — aylanma import xavfi yo'q, chunki `admin.service` ularni import qilmaydi).

`app/core/deps.py::get_current_user`ga qo'shimcha:
```python
if user.is_banned:
    raise ForbiddenError("Hisobingiz bloklangan")
```
(Har bir so'rovda tekshiriladi — bloklangan foydalanuvchining oldindan olingan tokeni ham darhol ishlamay qoladi, faqat yangi login emas.)

`app/modules/users/service.py::authenticate`ga qo'shimcha: parol tekshiruvidan keyin `if user.is_banned: raise ForbiddenError(...)`.

## Validatsiya

- `BanUserRequest.reason: str = Field(min_length=3)`
- `InviteAdminRequest` — `RegisterRequest`ga o'xshash, lekin `role` maydoni yo'q (doim `ADMIN`)
- `RejectRequest.reason: str = Field(min_length=3)` (Listings/Tours uchun umumiy)

## Test strategiyasi

`tests/test_admin.py`:
1. **Xavfsizlik**: `POST /auth/register` bilan `role=ADMIN` yuborish — 422
2. Oddiy user `/admin/*` endpointlariga kirishga urinsa — 403 (barcha endpointlar uchun)
3. Listing/tur rad etish — `rejected=True`, `reject_reason` saqlanadi, ommaviy qidiruvda ko'rinmaydi, audit yoziladi
4. Foydalanuvchi bloklash — bloklangach login qila olmaydi (401/403); mavjud tokeni bilan so'rov yuborsa 403; unban qilingach yana ishlaydi
5. `invite-admin` — yaratilgan user haqiqatan `role=ADMIN` bilan login qila oladi
6. `GET /admin/dashboard` — haqiqiy hisoblarni qaytaradi (test ma'lumotlari bilan solishtirib)
7. `GET /admin/moderation/listings`/`tours` — faqat kutayotganlarni qaytaradi
8. `GET /admin/audit-log` — amallar to'g'ri yoziladi va filtrlanadi
9. ADMIN listing'ni pause qila olishi (egasi bo'lmasa ham)

## Migratsiya

`alembic revision --autogenerate -m "admin moduli - audit log, ban, reject maydonlari"`. Yangi jadval + 3 ta mavjud jadvalga (`users`/`listings`/`tours`) ustun qo'shish — barchasi bitta migratsiyada, autogenerate to'liq aniqlashi kutiladi (yangi enum turlari bor, `create_type` muammosi kutilmaydi, chunki mavjud enumlarni qayta ishlatmaydi).

## Doiradan tashqari

- Trafik/analitika kuzatuvi (page-view/session events) — hech qanday infratuzilma yo'q
- Haqiqiy 2FA, login tarixi/sessiya kuzatuvi (parolsiz OTP+ishonchli-qurilma modeli — backend'ning hozirgi auth arxitekturasidan butunlay boshqacha)
- IP qora ro'yxati (frontendda ham kuchga kiritilmagan, foydalanuvchi ban'i bilan bir xil maqsadga xizmat qiladi, ortiqcha)
- Admin ruxsat darajalari (super-admin vs oddiy admin) — frontendda ham yo'q
