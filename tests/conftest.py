import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.core.db import Base, get_db
from app.core.security import create_token, hash_password
from app.main import app
from app.modules.users.models import User, UserRole

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    get_settings().database_url.rsplit("/", 1)[0] + "/damber_test",
)

engine = create_async_engine(TEST_DATABASE_URL)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _prepare_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )

        @event.listens_for(session.sync_session, "after_transaction_end")
        def _restart_savepoint(sess, transaction):
            if trans.is_active and transaction.nested and not transaction._parent.nested:
                sess.begin_nested()

        yield session

        await session.close()
        await trans.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _create_user(db_session: AsyncSession, role: UserRole, phone: str) -> User:
    user = User(
        name="Test",
        surname="User",
        phone=phone,
        email=f"{phone}@test.local",
        password_hash=hash_password("password123"),
        role=role,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def b2c_user(db_session: AsyncSession) -> User:
    return await _create_user(db_session, UserRole.B2C, "998900000001")


@pytest_asyncio.fixture
async def b2b_user(db_session: AsyncSession) -> User:
    return await _create_user(db_session, UserRole.B2B, "998900000002")


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    return await _create_user(db_session, UserRole.ADMIN, "998900000003")


def _auth_headers(user: User) -> dict[str, str]:
    token = create_token(str(user.id), "access", {"role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def b2c_headers(b2c_user: User) -> dict[str, str]:
    return _auth_headers(b2c_user)


@pytest.fixture
def b2b_headers(b2b_user: User) -> dict[str, str]:
    return _auth_headers(b2b_user)


@pytest.fixture
def admin_headers(admin_user: User) -> dict[str, str]:
    return _auth_headers(admin_user)
