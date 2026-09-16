import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import create_token, hash_password, verify_password
from app.modules.users.models import User
from app.modules.users.schemas import LoginRequest, RegisterRequest, TokenPair


def _normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone)


async def get_by_id(db: AsyncSession, user_id: str) -> User | None:
    return await db.get(User, user_id)


async def _find_by_identifier(db: AsyncSession, identifier: str) -> User | None:
    digits = _normalize_phone(identifier)
    if len(digits) >= 9:
        result = await db.execute(select(User).where(User.phone == digits))
        user = result.scalar_one_or_none()
        if user:
            return user
    result = await db.execute(select(User).where(User.email == identifier.lower()))
    return result.scalar_one_or_none()


async def register(db: AsyncSession, payload: RegisterRequest) -> User:
    phone = _normalize_phone(payload.phone) if payload.phone else None
    email = payload.email.lower() if payload.email else None

    if phone:
        existing = await db.execute(select(User).where(User.phone == phone))
        if existing.scalar_one_or_none():
            raise ConflictError("Bu telefon raqam allaqachon ro'yxatdan o'tgan")
    if email:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise ConflictError("Bu email allaqachon boshqa hisobga bog'langan")

    user = User(
        name=payload.name,
        surname=payload.surname,
        phone=phone,
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        biz_category=payload.biz_category,
        current_plan_id="free" if payload.role.value == "B2B" else None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, payload: LoginRequest) -> User:
    user = await _find_by_identifier(db, payload.identifier)
    if not user or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Login yoki parol noto'g'ri")
    if user.is_banned:
        raise ForbiddenError("Hisobingiz bloklangan")
    return user


def issue_tokens(user: User) -> TokenPair:
    claims = {"role": user.role.value}
    return TokenPair(
        access_token=create_token(str(user.id), "access", claims),
        refresh_token=create_token(str(user.id), "refresh"),
    )
