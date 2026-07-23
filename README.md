# DamBer Backend (FastAPI)

## Ishga tushirish (Docker — tavsiya etiladi)

Windows host'da antivirus/EDR (masalan ESET) ba'zan Docker portforward orqali
kelayotgan PostgreSQL binary protokolini (5432-port) buzadi — shu sabab server
ham DB bilan bir tarmoqda, konteynerda ishlaydi:

```bash
cd D:\projects\dam\backend
docker compose up -d --build
```

Health check: http://127.0.0.1:8000/health
Swagger docs: http://127.0.0.1:8000/docs

Kod `volumes: - .:/app` orqali bog'langan — fayllarni Windows'da tahrirlaysiz,
`fastapi dev` avtomatik reload qiladi. Loglarni ko'rish: `docker compose logs -f api`.

## Ishga tushirish (lokal .venv — agar antivirus 5432-portni bloklamasa)

```bash
cd D:\projects\dam\backend
.venv\Scripts\activate
copy .env.example .env   # so'ng JWT_SECRET va DATABASE_URL ni to'ldiring
docker compose up -d db  # faqat PostgreSQL
fastapi dev app/main.py
```

Agar `asyncpg`/`psycopg` ulanishda "connection was closed in the middle of
operation" xatosi bersa — bu deyarli har doim antivirus/EDR tarmoq filtri.
ESET'da: Setup → Network protection → Firewall → qoida qo'shing (TCP,
127.0.0.1, port 5432, Allow) yoki shu jarayonni protokol tekshiruvidan
istisno qiling. Tasdiqlash uchun real-time himoyani vaqtincha o'chirib sinang.

## Struktura

```
app/
  core/       # config, db session, security (JWT), exceptions, auth deps
  modules/    # vertical slice: har modul o'z models/schemas/service/router bilan
    users/    # tayyor: register/login/me
    listings/ # navbatdagi bosqich
    bookings/ # navbatdagi bosqich (eskrov mantig'i shu yerda bo'ladi)
    wallet/   # navbatdagi bosqich
  main.py
migrations/   # Alembic
```

## Migratsiyalar

Yangi model modul qo'shganda `migrations/env.py` ichidagi importlar ro'yxatiga
model faylini qo'shing (Base.metadata to'liq bo'lishi uchun), so'ng:

```bash
docker compose exec api alembic revision --autogenerate -m "nimadir qo'shildi"
docker compose exec api alembic upgrade head
```

(Lokal `.venv`dan portforward orqali xato bersa — yuqoridagi antivirus eslatmasiga qarang.)

## Test

```bash
pytest
```
