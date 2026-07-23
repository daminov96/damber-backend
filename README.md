# DamBer Backend (FastAPI)

## Ishga tushirish

```bash
cd D:\projects\dam\backend
.venv\Scripts\activate
copy .env.example .env   # so'ng JWT_SECRET va DATABASE_URL ni to'ldiring
fastapi dev app/main.py
```

Health check: http://127.0.0.1:8000/health
Swagger docs: http://127.0.0.1:8000/docs

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
alembic revision --autogenerate -m "nimadir qo'shildi"
alembic upgrade head
```

## Test

```bash
pytest
```
