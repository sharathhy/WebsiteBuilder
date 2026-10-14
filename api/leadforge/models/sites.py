import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from leadforge.db.base import Base, Timestamps, UUIDPk, str_enum
from leadforge.models.enums import GeneratedSiteStatus


class GeneratedSite(UUIDPk, Timestamps, Base):
    """A replacement site built from a JSON site spec and deployed as a noindex preview."""

    __tablename__ = "generated_sites"

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    template: Mapped[str] = mapped_column(String(50))
    spec_version: Mapped[str] = mapped_column(String(20))
    site_spec: Mapped[dict[str, Any]] = mapped_column(default=dict)
    status: Mapped[GeneratedSiteStatus] = mapped_column(
        str_enum(GeneratedSiteStatus, "generated_site_status"), default=GeneratedSiteStatus.QUEUED
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    preview_url: Mapped[str | None] = mapped_column(String(2048))
    vercel_project_id: Mapped[str | None] = mapped_column(String(100))
    vercel_deployment_id: Mapped[str | None] = mapped_column(String(100))
    noindex: Mapped[bool] = mapped_column(Boolean, default=True)
    score: Mapped[int | None] = mapped_column(Integer)
    baseline_score: Mapped[int | None] = mapped_column(Integer)
    custom_domain: Mapped[str | None] = mapped_column(String(255))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    # Which of the current site's pages answer on the preview: {expected, present, missing, pages}
    page_parity: Mapped[dict[str, Any] | None] = mapped_column()


class FormSubmission(UUIDPk, Timestamps, Base):
    """A contact-form message from a generated site. While the site is only a preview the
    message is stored, never forwarded, so we don't email the business uninvited."""

    __tablename__ = "form_submissions"

    generated_site_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("generated_sites.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    forwarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
