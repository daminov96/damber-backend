# Admin rol darajalari + foydalanuvchilar boshqaruvini frontend'ga ulash — dizayn

**Sana**: 2026-08-28
**Holat**: Taklif (foydalanuvchi tasdig'ini kutmoqda)
**Bog'liq**: `2026-07-30-admin-module-design.md` (bu spec o'shani kengaytiradi — asosiy admin moduli, `is_banned`, audit log, `invite-admin` allaqachon qurilgan va commit qilingan)

## Kontekst

Frontend audit (Explore agent, 2026-08-28) shuni ko'rsatdi: `damber-front` (`24082026_2`)da admin foydalanuvchilar boshqaruvi ikkita parallel, ikkalasi ham backend'ga ulanmagan tizimdan iborat:

1. **`AdminUsersControl.tsx`** — faqat mock IP qora ro'yxatini ko'rsatadi (3 ta qattiq kodlangan IP). Haqiqiy foydalanuvchi ro'yxati/ban backend'da (`GET /admin/users`, `POST /admin/users/{id}/ban`/`unban`) allaqachon tayyor, lekin frontend ulanmagan.
2. **`AdminTeam.tsx` + `store/admin.ts`** — to'rt darajali rol tizimi (`super`/`moderator`/`finance`/`content`, `ROLE_MATRIX` — qaysi rol qaysi panel bo'limiga kira oladi) bilan "Adminlar jamoasi" ekrani. To'liq lokal (`teamAdmins`, `addAdmin`, `removeAdmin`, `setAdminRole`) — backend'dagi `invite-admin` esa rol darajasini bilmaydi, bitta `ADMIN` roli bor.
3. **`store/auth.ts`**dagi `adminSetRole`/`adminAdjustWallet`/`adminSetPlanFor`/`adminCreateUser`/`adminDeleteUser` — UI'da hech qayerda chaqirilmaydi, o'lik kod.
4. **`AdminActivityLog.tsx`** — lokal `store/admin.ts::logEntries` dan o'qiydi, backend'dagi haqiqiy audit-log (`GET /admin/audit-log`) bilan bog'lanmagan.

Foydalanuvchi bilan qaror qilindi: frontend'dagi 4-darajali rol tizimi **saqlanadi va backend'ga ko'chiriladi** (soddalashtirilmaydi) — chunki bu allaqachon ishlab chiqilgan, mazmunli xavfsizlik modeli (moderator narxga tegolmasligi kerak degan asl sabab bilan).

## Loyihachi qarorlar

### Rol darajalari — backend domenining qismiga aylanadi

`AdminRole` (`super`/`moderator`/`finance`/`content`) va `ROLE_MATRIX` (rol → ruxsat etilgan modullar to'plami) endi **backend'da qat'iy belgilanadi**, `plans/catalog.py` naqshiga o'xshab (DB jadvali emas — Python kod, chunki matritsa kod bilan birga o'zgaradi, ma'muriy tahrirlash kerak emas). Frontend endi bu ikkalasini o'zi belgilamaydi — backend'dan (`GET /users/me` javobidagi `admin_role` + kod ichida saqlangan `ROLE_MATRIX`ning frontend nusxasi, mos ravishda) foydalanadi.

**Nima uchun kod, DB emas**: `plans`dagi bilan bir xil mulohaza — bu qat'iy, kichik, deploy paytida biladigan to'plam; DB jadvali bo'lsa ma'nosiz boshqaruv UI kerak bo'lardi (kim rolga qaysi modulni tayinlaydi — o'zi alohida "ruxsat boshqarish" funksiyasi bo'lib ketardi, so'ralmagan).

### Server-side enforcement — har bir endpoint o'z modulini tekshiradi

Hozir barcha `/admin/*` endpointlar bitta `require_role(ADMIN)`ga bog'liq. Bu **saqlanadi birinchi qatlam sifatida** (ADMIN bo'lmagan hech kim admin panelga kira olmaydi), ustiga **ikkinchi qatlam** qo'shiladi: `require_admin_module(module)` — `current_user.admin_role`ning `ROLE_MATRIX[admin_role]`da shu modul borligini tekshiradi, aks holda 403. Bu ataylab **enforcement backend'da** — frontend'dagi UI-qulflash (bo'lim ko'rinmasligi) faqat qulaylik, haqiqiy chegara serverda.

### Nima frontend'dan meros olinadi, nima backend'da yangi

| Frontend qismi | Qaror |
|---|---|
| `ROLE_MATRIX` mazmuni (8 modul: moderation/users/finance/bookings/content/analytics/settings/team) | Backend'ga so'zma-so'z ko'chiriladi |
| `teamAdmins`/`addAdmin`/`removeAdmin`/`setAdminRole` (`store/admin.ts`) | Backend chaqiruvlariga almashtiriladi, lokal state o'chadi |
| `AdminTeam.tsx` UI (jadval, huquq matritsasi ko'rsatish, forma) | Saqlanadi, ma'lumot manbai backend'ga almashadi |
| `AdminUsersControl.tsx` mock IP-ban | **Saqlanadi** (foydalanuvchi tanlovi — dekorativ bo'lib qoladi, backend'da mos tushuncha yo'q) |
| `AdminUsersControl.tsx` — haqiqiy foydalanuvchi ro'yxati/ban | **Yangi qo'shiladi** — hozir bu ekranda umuman yo'q edi |
| `AdminActivityLog.tsx` | Backend `GET /admin/audit-log`ga o'tadi |
| `store/auth.ts` o'lik admin funksiyalari | O'chiriladi |

## Ma'lumotlar modeli

**`app/modules/users/models.py`ga qo'shimcha**:
```python
class AdminRole(enum.StrEnum):
    super = "super"
    moderator = "moderator"
    finance = "finance"
    content = "content"

# User modeliga:
admin_role: Mapped[AdminRole | None] = mapped_column(Enum(AdminRole), nullable=True)
```
Faqat `role == UserRole.ADMIN` bo'lgan userlarda mazmunli; boshqalarda doim `None`. DB darajasida CHECK constraint qo'shiladi: `role == 'ADMIN'` bo'lmasa `admin_role IS NULL` bo'lishi shart (Guides/Tours modulidagi polimorfik-egalik CHECK constraint naqshiga o'xshab, avtogenerate buni aniqlamaydi — qo'lda qo'shiladi).

**`app/modules/admin/permissions.py`** (yangi fayl):
```python
class AdminModule(enum.StrEnum):
    moderation = "moderation"
    users = "users"
    finance = "finance"
    bookings = "bookings"
    content = "content"
    analytics = "analytics"
    settings = "settings"
    team = "team"

ROLE_MATRIX: dict[AdminRole, frozenset[AdminModule]] = {
    AdminRole.super: frozenset(AdminModule),  # hammasi
    AdminRole.moderator: frozenset({AdminModule.moderation, AdminModule.users, AdminModule.bookings, AdminModule.analytics}),
    AdminRole.finance: frozenset({AdminModule.finance, AdminModule.bookings, AdminModule.analytics}),
    AdminRole.content: frozenset({AdminModule.content, AdminModule.moderation, AdminModule.analytics}),
}
```
(Frontend'dagi `ROLE_MATRIX` bilan bir xil mazmun — `store/admin.ts:90-104`.)

## Endpoints

### `app/core/deps.py`ga qo'shimcha

```python
def require_admin_module(module: AdminModule):
    async def _check(current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))]) -> User:
        if module not in ROLE_MATRIX.get(current_user.admin_role, frozenset()):
            raise ForbiddenError("Bu bo'limga kirish huquqingiz yo'q")
        return current_user
    return _check
```

### `app/modules/admin/router.py` — mavjud endpointlarga modul tayinlash

| Method | Path | Modul |
|---|---|---|
| GET | `/admin/dashboard` | `analytics` |
| GET | `/admin/users` | `users` |
| POST | `/admin/users/{id}/ban` | `users` |
| POST | `/admin/users/{id}/unban` | `users` |
| POST | `/admin/users/invite-admin` | `team` |
| GET | `/admin/moderation/listings` | `moderation` |
| GET | `/admin/moderation/tours` | `moderation` |
| GET | `/admin/audit-log` | `settings` (mavjud panel joylashuvi bilan mos — jurnal "Sozlamalar" ostida) |

### Yangi endpointlar

| Method | Path | Tavsif | Modul |
|---|---|---|---|
| PATCH | `/admin/users/{user_id}/admin-role` | `{admin_role}` — faqat `super`. O'zini pasaytira olmaydi (403). Tizimdagi yagona `super`ni pasaytirib bo'lmaydi (409). Faqat `role == ADMIN` userlarga qo'llanadi (404 aks holda). | `team` |
| DELETE | `/admin/users/{user_id}` | Faqat `super`. O'zini o'chira olmaydi (403). Yagona `super`ni o'chirib bo'lmaydi (409). Faqat `role == ADMIN` userlarga (404 aks holda — oddiy foydalanuvchini bu endpoint o'chirmaydi, ataylab: user o'chirish butunlay boshqa, so'ralmagan funksiya). | `team` |

`InviteAdminRequest`ga qo'shimcha: `admin_role: AdminRole` (majburiy).

`UserOut`ga qo'shimcha: `admin_role: AdminRole | None`.

Yangi audit action'lar (`AuditAction` enumiga): `admin_role_change`, `admin_delete`.

## Service funksiyalari

`app/modules/admin/service.py`ga qo'shimcha:
```python
async def set_admin_role(db, user_id, current_admin, new_role: AdminRole) -> User:
    # current_admin.admin_role != super → ForbiddenError
    # user_id == current_admin.id → ForbiddenError("O'zingizning huquq darajangizni o'zgartira olmaysiz")
    # target topilmadi yoki target.role != ADMIN → NotFoundError
    # target.admin_role == super va bu SO'NGGI super (boshqa super yo'q) va new_role != super → ConflictError
    # ... admin_role = new_role, log_action(admin_role_change)

async def delete_admin(db, user_id, current_admin) -> None:
    # xuddi shu tekshiruvlar (o'zini o'chira olmaydi, so'nggi super'ni o'chirib bo'lmaydi)
    # log_action(admin_delete) — o'chirishdan OLDIN yoziladi (target_id hali mavjud bo'lishi kerak)
```

`invite_admin()` mavjud implementatsiyasi `payload.admin_role`ni `User.admin_role`ga yozadigan qilib yangilanadi.

## Migratsiya

1. `alembic revision --autogenerate -m "admin rol darajalari"` — `admin_role` ustuni + CHECK constraint (qo'lda qo'shiladi, avtogenerate aniqlamaydi).
2. **Ma'lumot migratsiyasi**: mavjud `role == ADMIN` foydalanuvchilar orasidan **eng birinchi yaratilgani** (`created_at ASC LIMIT 1`) `admin_role = 'super'` bilan boshlanadi, qolganlari `'moderator'` bilan (xavfsiz sukut — kengroq huquq emas). Bitta migratsiya faylida `op.execute()` orqali qo'lda yoziladi (Alembic autogenerate buni bilmaydi).

## Frontend o'zgarishlar

### `src/store/auth.ts`
- O'chiriladi: `adminSetRole`, `adminAdjustWallet`, `adminSetPlanFor`, `adminCreateUser`, `adminDeleteUser` (interfeys va implementatsiya).
- `mapBackendUser`ga `admin_role` maydoni qo'shiladi (`User` tipiga ham).

### `src/store/admin.ts`
- O'chiriladi: `teamAdmins`, `addAdmin`, `removeAdmin`, `setAdminRole`, `TeamAdmin` interfeysi, `logEntries`, `addLog`, `AdminLogEntry`, `SEED_LOG`, `LOG_LIMIT`, `AdminLogAction` (backend audit-log bilan almashadi).
- Saqlanadi: `blacklistedIps`/`banIp`/`unbanIp` (dekorativ, foydalanuvchi tanlovi bo'yicha), `profileStatus`/`rejections`/`checkedDocs`/`hiddenReviews`/`autoShield` — bu safar qamrovdan tashqari, tegilmaydi.
- `ROLE_MATRIX`/`ROLE_LABELS`/`AdminRole`/`AdminModule`/`roleCan` — **saqlanadi** (UI-qulflash uchun hamon kerak — backend'dan kelgan `admin_role` bilan lokal matritsa solishtiriladi; matritsa mazmuni backend bilan qo'lda sinxron ushlab turiladi, chunki ikkalasi ham kod, DB emas).

### Yangi: `src/store/adminUsers.ts`
Backend bilan ishlaydigan yangi store (mavjud `myListings.ts` naqshiga o'xshab):
- `users: BackendUser[]`, `total`, `page`, filtrlar — `fetchUsers({role?, isBanned?, query?, page})` → `GET /admin/users`
- `banUser(userId, reason)` → `POST /admin/users/{id}/ban`
- `unbanUser(userId)` → `POST /admin/users/{id}/unban`
- `inviteAdmin(input)` → `POST /admin/users/invite-admin`
- `setAdminRole(userId, role)` → `PATCH /admin/users/{id}/admin-role`
- `deleteAdmin(userId)` → `DELETE /admin/users/{id}`
- `auditLog: AuditLogEntry[]`, `fetchAuditLog({action?, page})` → `GET /admin/audit-log`

### `AdminUsersControl.tsx`
- Yangi bo'lim qo'shiladi (mock IP jadvalidan OLDIN): haqiqiy foydalanuvchilar jadvali — `adminUsers.users`dan, qidiruv/rol/ban filtri, "Bloklash" tugmasi sabab kiritish uchun kichik modal ochadi (`banUser`), bloklangan userlarda "Blokdan chiqarish" (`unbanUser`).
- Mavjud mock IP-ban bo'limi o'zgarishsiz qoladi.

### `AdminTeam.tsx`
- `teamAdmins` → `adminUsers.users.filter(u => u.role === "ADMIN")` (backend'dan `role=ADMIN` filtri bilan so'raladi).
- `addAdmin` chaqiruvi → `adminUsers.inviteAdmin()`.
- `removeAdmin` → `adminUsers.deleteAdmin()`.
- `setAdminRole` (select onChange) → `adminUsers.setAdminRole()`.
- Huquqlar matritsasi jadvali (`ROLE_MATRIX` ko'rsatish) — o'zgarishsiz (hamon lokal `ROLE_MATRIX` konstantadan, chunki bu faqat ko'rsatish, backend'dan olib kelish shart emas).
- Bo'limning o'zi joriy foydalanuvchi `admin_role !== "super"` bo'lsa `roleCan(currentAdminRole, "team")`ga ko'ra yashirin qoladi (mavjud panel-qulflash naqshi — qayerda ekanini implementatsiya bosqichida `AdminPanel`/`page.tsx` marshrutida tekshiramiz).

### `AdminActivityLog.tsx`
- `useAdmin().logEntries` → `adminUsers.auditLog` (backend, `fetchAuditLog()` orqali). Ko'rsatish maydonlari (`action`/`target`/`detail`/`vaqt`) backend `AuditLogEntryOut` (`action`/`target_type`+`target_id`/`detail`/`created_at`)dan moslashtiriladi — kichik adapter funksiya (`target_type: "user", target_id: <uuid>` → ko'rsatish uchun matn birlashtirish, masalan `"user #a1b2c3"`; to'liq ism kerak bo'lsa keyingi bosqichda backend `detail`ga yozadi, hozircha `target_id` qisqartirilib ko'rsatiladi).

## Test strategiyasi

`tests/test_admin.py`ga qo'shimcha:
1. `require_admin_module` birlik testi: `ROLE_MATRIX`da bo'lmagan modul so'ralganda 403, bor bo'lganda o'tkazib yuborishi (endpoint darajasida emas, dependency funksiyasining o'zida) — `finance` moduliga endpoint hali yo'qligi sababli xatti-harakat shu darajada tekshiriladi. `moderator` `/admin/users`ga kira olishi (ROLE_MATRIX'da bor) — integratsion test sifatida.
2. `super` bo'lmagan admin `invite-admin`/`admin-role`/`DELETE /admin/users/{id}` chaqirsa 403.
3. `super` o'zini pasaytirsa/o'chirsa 403.
4. Yagona `super`ni pasaytirish/o'chirish — 409.
5. `invite_admin` bilan yaratilgan admin `admin_role` to'g'ri saqlanganini tekshirish, u bilan login qilib mos modullarga kira olishi/kirolmasligi.
6. Migratsiya: eng birinchi ADMIN `super`, qolganlari `moderator` bo'lib chiqishi (data-migration testi yoki qo'lda tekshiruv).

Frontend: `store/admin.test.ts`dan o'chirilgan funksiyalar (`addAdmin`/`removeAdmin`/`setAdminRole`) testlari olib tashlanadi; yangi `adminUsers.ts` uchun testlar yoziladi (mavjud `myListings`/`chat` store testlari naqshiga o'xshab, `apiFetch` mock qilinadi).

### `tests/conftest.py` — mavjud fixture yangilanishi

`admin_user`/`admin_headers` fixture'lari hozir `admin_role`siz ADMIN yaratadi. `ROLE_MATRIX.get(admin_role, frozenset())` — `admin_role=None` bo'lsa hech qanday modulga ruxsat bermaydi, bu mavjud testlarni (`admin_headers` ishlatuvchi hammasi) buzadi. Shu sababli `_create_user`ga `admin_role: AdminRole | None = None` parametri qo'shiladi, `admin_user` fixture endi `admin_role=AdminRole.super` bilan yaratiladi (yagona test-ADMIN — production migratsiyadagi "birinchi ADMIN = super" qoidasiga mos). Rol-cheklangan testlar uchun yangi `moderator_user`/`moderator_headers` fixture qo'shiladi (`admin_role=AdminRole.moderator`).

## Doiradan tashqari

- `adminAdjustWallet`/`adminSetPlanFor` ekvivalenti backend'da — balans qo'lda tuzatish, tarif qo'lda tayinlash: alohida spec/ish, bu safar qamrab olinmaydi (foydalanuvchi tasdiqladi).
- Oddiy (ADMIN bo'lmagan) foydalanuvchini o'chirish — faqat ban orqali boshqariladi, `DELETE` endpoint faqat admin-hisoblar uchun.
- IP qora ro'yxatini backend'ga ulash — dekorativ holida qoladi (foydalanuvchi tanlovi).
- Ruxsat darajalarini DB-boshqariladigan (admin panel orqali tahrirlanadigan) qilish — bu safar statik kod sifatida qoladi.
