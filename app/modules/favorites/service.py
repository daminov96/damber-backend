import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.favorites.models import Favorite
from app.modules.favorites.schemas import FavoriteCreateRequest
from app.modules.users.models import User


async def create(db: AsyncSession, user: User, payload: FavoriteCreateRequest) -> Favorite:
    existing = (
        await db.execute(
            select(Favorite.id).where(
                Favorite.user_id == user.id, Favorite.listing_id == payload.listing_id
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictError("Bu e'lon allaqachon sevimlilarda")

    favorite = Favorite(user_id=user.id, listing_id=payload.listing_id)
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)
    return favorite


async def list_mine(
    db: AsyncSession, user: User, page: int, page_size: int
) -> tuple[list[Favorite], int]:
    count_stmt = select(func.count()).select_from(Favorite).where(Favorite.user_id == user.id)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Favorite)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def remove(db: AsyncSession, user: User, listing_id: uuid.UUID) -> None:
    favorite = (
        await db.execute(
            select(Favorite).where(Favorite.user_id == user.id, Favorite.listing_id == listing_id)
        )
    ).scalar_one_or_none()
    if not favorite:
        raise NotFoundError("Sevimlilarda topilmadi")

    await db.delete(favorite)
    await db.commit()
