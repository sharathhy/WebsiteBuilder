import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from leadforge.db.base import Base, Timestamps, UUIDPk, str_enum
from leadforge.models.enums import AuditStatus, Grade, Viewport


class Audit(UUIDPk, Timestamps, Base):
    """One scoring run against either an existing website or a generated site."""

    __tablename__ = "audits"
    __table_args__ = (
        CheckConstraint(
            "(website_id IS NOT NULL) <> (generated_site_id IS NOT NULL)", name="one_target"
        ),
        CheckConstraint("total_score IS NULL OR (total_score BETWEEN 0 AND 100)", name="score"),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    website_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("websites.id", ondelete="CASCADE"), index=True
    )
    generated_site_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("generated_sites.id", ondelete="CASCADE"), index=True
    )
    target_url: Mapped[str] = mapped_column(String(2048))
    rubric_version: Mapped[str] = mapped_column(String(20))
    status: Mapped[AuditStatus] = mapped_column(
        str_enum(AuditStatus, "audit_status"), default=AuditStatus.QUEUED
    )
    total_score: Mapped[int | None] = mapped_column(Integer)
    grade: Mapped[Grade | None] = mapped_column(str_enum(Grade, "grade"))
    # {"performance": {"score": 12, "max": 20}, ...}
    breakdown: Mapped[dict[str, Any]] = mapped_column(default=dict)
    evidence: Mapped[dict[str, Any]] = mapped_column(default=dict)
    # Plain-language issues, e.g. "Your site takes 9.4s to load on phones".
    top_issues: Mapped[list[Any]] = mapped_column(default=list)
    error: Mapped[str | None] = mapped_column(Text)
    cached_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Screenshot(UUIDPk, Timestamps, Base):
    __tablename__ = "screenshots"

    audit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("audits.id", ondelete="CASCADE"), index=True
    )
    viewport: Mapped[Viewport] = mapped_column(str_enum(Viewport, "viewport"))
    storage_key: Mapped[str] = mapped_column(String(1024))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
