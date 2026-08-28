"""Migratsiya `840fb5257f2f_admin_rol_darajalari.py`ning ma'lumot
migratsiyasi (mavjud ADMIN foydalanuvchilarni `admin_role`ga to'ldirish)
qismini sinaydi.

Test DB Alembic orqali emas, `Base.metadata.create_all` orqali quriladi
(`conftest.py::_prepare_database`) — shuning uchun Alembic runnerni bu
yerda ishga tushirish shart emas va noqulay bo'lardi (alohida engine/
tranzaksiya boshqaruvi talab qiladi). Buning o'rniga migratsiya faylidagi
aynan shu SQL ibora ustida sinaymiz — bu SQL mantig'ining o'zini tekshiradi,
Alembic runner infratuzilmasini emas."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import AdminRole, User, UserRole

# `migrations/versions/840fb5257f2f_admin_rol_darajalari.py::upgrade()`dagi
# ma'lumot migratsiyasi bilan so'zma-so'z bir xil ikkita ibora.
_PROMOTE_FIRST_TO_SUPER = """
    UPDATE users SET admin_role = 'super'
    WHERE id = (
        SELECT id FROM users WHERE role = 'ADMIN'
        ORDER BY created_at ASC LIMIT 1
    )
"""
_REST_TO_MODERATOR = (
    "UPDATE users SET admin_role = 'moderator' "
    "WHERE role = 'ADMIN' AND admin_role IS NULL"
)


async def _create_admin(db_session: AsyncSession, phone: str) -> User:
    from app.core.security import hash_password

    user = User(
        name="Test",
        surname="Admin",
        phone=phone,
        email=f"{phone}@test.local",
        password_hash=hash_password("password123"),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestAdminRoleDataMigration:
    async def test_first_created_admin_becomes_super_rest_moderator(
        self, db_session: AsyncSession
    ):
        first = await _create_admin(db_session, "998900000101")
        second = await _create_admin(db_session, "998900000102")
        third = await _create_admin(db_session, "998900000103")

        await db_session.execute(text(_PROMOTE_FIRST_TO_SUPER))
        await db_session.execute(text(_REST_TO_MODERATOR))
        await db_session.commit()

        await db_session.refresh(first)
        await db_session.refresh(second)
        await db_session.refresh(third)

        assert first.admin_role == AdminRole.super
        assert second.admin_role == AdminRole.moderator
        assert third.admin_role == AdminRole.moderator

    async def test_non_admin_users_untouched(self, db_session: AsyncSession, b2c_user: User):
        await _create_admin(db_session, "998900000104")

        await db_session.execute(text(_PROMOTE_FIRST_TO_SUPER))
        await db_session.execute(text(_REST_TO_MODERATOR))
        await db_session.commit()

        await db_session.refresh(b2c_user)
        assert b2c_user.admin_role is None
