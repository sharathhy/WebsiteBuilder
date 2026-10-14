from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from leadforge.db.base import Base, Timestamps, UUIDPk, str_enum
from leadforge.models.enums import Role


class User(UUIDPk, Timestamps, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[Role] = mapped_column(str_enum(Role, "role"), default=Role.REVIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
