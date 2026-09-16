import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.modules.users.models import AdminRole, UserRole


class RegisterRequest(BaseModel):
    name: str
    surname: str
    password: str = Field(min_length=6)
    role: Literal[UserRole.B2C, UserRole.B2B] = UserRole.B2C
    phone: str | None = None
    email: EmailStr | None = None
    biz_category: str | None = None

    @model_validator(mode="after")
    def _phone_or_email(self) -> "RegisterRequest":
        if not self.phone and not self.email:
            raise ValueError("Telefon raqam yoki email kiriting")
        return self


class LoginRequest(BaseModel):
    identifier: str  # telefon yoki email
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    surname: str
    phone: str | None
    email: str | None
    role: UserRole
    wallet_balance: float
    is_premium: bool
    current_plan_id: str | None
    biz_category: str | None
    city: str | None
    avatar_url: str | None
    is_banned: bool
    admin_role: AdminRole | None
