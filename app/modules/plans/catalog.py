"""B2B tarif rejalari — statik katalog (DB jadvali emas).

Frontend porti: src/data/plans.ts. 4 ta qat'iy tarif, kod darajasida
belgilangan. Matn/qiymatlar frontend bilan so'z-ma-so'z bir xil.
"""

import enum
from dataclasses import dataclass, field


class PlanId(enum.StrEnum):
    free = "free"
    standard = "standard"
    business = "business"
    premium = "premium"


@dataclass(frozen=True)
class PlanDefinition:
    id: PlanId
    name: str
    price: float
    photo_limit: int
    video_limit: int
    video_size_mb: int
    badge: str | None
    emblem: str | None
    features: list[str] = field(default_factory=list)


PLAN_CATALOG: dict[PlanId, PlanDefinition] = {
    PlanId.free: PlanDefinition(
        id=PlanId.free,
        name="Bepul",
        price=0,
        photo_limit=10,
        video_limit=0,
        video_size_mb=0,
        badge=None,
        emblem=None,
        features=[
            "1 ta e'lon joylashtirish",
            "10 tagacha rasm yuklash",
            "Video yuklash imkoni yo'q",
            "Oddiy tartibda ko'rinadi",
        ],
    ),
    PlanId.standard: PlanDefinition(
        id=PlanId.standard,
        name="Standart",
        price=150_000,
        photo_limit=20,
        video_limit=1,
        video_size_mb=30,
        badge=None,
        emblem=None,
        features=[
            "3 ta e'lon joylashtirish",
            "20 tagacha rasm + 1 video (30 MB gacha)",
            "Bir necha marta yuqoriga ko'tarish imkoniyati",
            "Analitika va statistika",
            "30 kun amal qiladi",
        ],
    ),
    PlanId.business: PlanDefinition(
        id=PlanId.business,
        name="Biznes",
        price=300_000,
        photo_limit=30,
        video_limit=2,
        video_size_mb=50,
        badge="Tavsiya etamiz",
        emblem="TOP",
        features=[
            "7 ta e'lon joylashtirish",
            "30 tagacha rasm + 2 video (50 MB gacha)",
            "Qidiruvda doimiy TOP 30 da ko'rinadi",
            "TOP nishoni beriladi",
            "Analitika va statistika",
            "30 kun amal qiladi",
        ],
    ),
    PlanId.premium: PlanDefinition(
        id=PlanId.premium,
        name="Premium VIP",
        price=450_000,
        photo_limit=50,
        video_limit=3,
        video_size_mb=100,
        badge=None,
        emblem="👑",
        features=[
            "15+ e'lon joylashtirish",
            "50 tagacha rasm + 3 video (100 MB gacha)",
            "Bosh sahifa va VIP blokda ko'rsatiladi",
            "👑 VIP / Premium nishoni",
            "Reklama bannerlarida ko'rinish",
            "Analitika va statistika",
            "30 kun amal qiladi",
        ],
    ),
}


def yearly_price(monthly_price: float) -> float:
    """Yillik to'lovda 16% chegirma."""
    return round(monthly_price * 12 * 0.84)
