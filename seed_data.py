"""Bir martalik test-ma'lumot skripti: mobile MVP'ni ko'rish uchun bir nechta
verified listing va tour yaratadi. Docker konteyner ichida ishga tushiriladi:

    docker compose exec api python /app/seed_data.py

Idempotent emas — qayta ishga tushirilsa yana nusxa yaratadi, shuning uchun
faqat bir marta ishlatiladi (yoki oldin DB tozalanadi).
"""

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

import app.main  # noqa: F401 -- barcha modul modellarini import qilib Base.metadata'ni to'ldiradi
from app.core.db import engine
from app.core.security import hash_password
from app.modules.guides.models import Guide, GuideEmployment, GuideType
from app.modules.listings.models import Listing, ListingType, Region
from app.modules.operators.models import OperatorSpecTag, TourOperator
from app.modules.tours.models import Tour, TourDifficulty
from app.modules.users.models import User, UserRole


async def main() -> None:
    async with AsyncSession(engine) as db:
        owner = User(
            name="Test",
            surname="Owner",
            phone="998901112233",
            email="owner@test.local",
            password_hash=hash_password("password123"),
            role=UserRole.B2B,
        )
        db.add(owner)
        await db.flush()

        listings_data = [
            ("Bo'stonliq tog' dachasi", ListingType.Dacha, Region.Bostanliq, 450000, 600000, 6),
            ("Samarqand butik mehmonxonasi", ListingType.Boutique, Region.Samarkand, 800000, 1000000, 4),
            ("Buxoro tarixiy mehmonxona", ListingType.Hotel, Region.Bukhara, 650000, 850000, 8),
            ("Xiva karvon-saroy villasi", ListingType.Villa, Region.Khiva, 1200000, 1500000, 10),
            ("Zomin dam olish maskani", ListingType.Recreation, Region.Zomin, 350000, 450000, 5),
        ]
        for name, ltype, region, wd, we, cap in listings_data:
            db.add(
                Listing(
                    owner_id=owner.id,
                    name=name,
                    type=ltype,
                    region=region,
                    weekday_price=wd,
                    weekend_price=we,
                    capacity=cap,
                    amenities=["wifi", "parking"],
                    description=f"{name} — test uchun yaratilgan namunaviy e'lon.",
                    verified=True,
                    paused=False,
                )
            )

        operator = TourOperator(
            owner_id=owner.id,
            name="DamBer Tour Operator",
            tin="123456789",
            license="LIC-0001",
            founded=2015,
            spec_tag=OperatorSpecTag.Tarixiy,
            phone="+998901112233",
            email="operator@test.local",
            office="Toshkent sh., Amir Temur ko'chasi 1",
            region=Region.Tashkent,
            description="Test tur operatori — namunaviy turlar uchun.",
        )
        db.add(operator)
        await db.flush()

        tours_data = [
            ("Samarqand-Buxoro 3 kunlik tur", Region.Samarkand, 1500000),
            ("Xiva tarixiy shahar sayohati", Region.Khiva, 900000),
            ("Chimyon tog' trekkingi", Region.Bostanliq, 400000),
        ]
        for name, region, price in tours_data:
            db.add(
                Tour(
                    operator_id=operator.id,
                    guide_id=None,
                    owner_id=owner.id,
                    name=name,
                    duration="3 kun 2 kecha",
                    region=region,
                    meeting_point="Toshkent, bosh vokzal",
                    difficulty=TourDifficulty.Ortacha,
                    price=price,
                    description=f"{name} — test uchun yaratilgan namunaviy tur.",
                    pending=False,
                    rejected=False,
                )
            )

        await db.commit()
        print("Seed muvaffaqiyatli yakunlandi: 1 owner, 5 listing, 1 operator, 3 tour.")


if __name__ == "__main__":
    asyncio.run(main())
