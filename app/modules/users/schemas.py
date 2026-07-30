import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.users.models import UserRole


class RegisterRequest(BaseModel):
    name: str
    surname: str
    phone: str
    password: str = Field(min_length=6)
    role: Literal[UserRole.B2C, UserRole.B2B] = UserRole.B2C
    email: EmailStr | None = None
    biz_category: str | None = None


class LoginRequest(BaseModel):
    identifier: str  # telefon yoki email
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    surname: str
    phone: str
    email: str | None
    role: UserRole
    wallet_balance: float
    is_premium: bool
    current_plan_id: str | None
    city: str | None
    avatar_url: str | None
    is_banned: bool
