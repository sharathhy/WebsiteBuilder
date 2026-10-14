import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from leadforge.models.enums import Role


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str  # output only; seeded dev users use the reserved .local TLD
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field("", max_length=200)
    password: str = Field(min_length=12, max_length=128)
    role: Role = Role.REVIEWER


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=200)
    role: Role | None = None
    is_active: bool | None = None
