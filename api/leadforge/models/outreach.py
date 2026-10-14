import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from leadforge.db.base import Base, Timestamps, UUIDPk, str_enum
from leadforge.models.enums import DraftStatus, EmailEventType, OutreachChannel


class EmailDraft(UUIDPk, Timestamps, Base):
    """An outreach message. Nothing is sent unless a human moves it to APPROVED."""

    __tablename__ = "email_drafts"

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL")
    )
    generated_site_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("generated_sites.id", ondelete="SET NULL")
    )
    channel: Mapped[OutreachChannel] = mapped_column(
        str_enum(OutreachChannel, "outreach_channel"), default=OutreachChannel.EMAIL
    )
    variant: Mapped[str] = mapped_column(String(8), default="A")
    subject: Mapped[str | None] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[DraftStatus] = mapped_column(
        str_enum(DraftStatus, "draft_status"), default=DraftStatus.DRAFTED, index=True
    )
    # 0 = initial, 3 / 7 = follow-up day offsets.
    sequence_day: Mapped[int] = mapped_column(Integer, default=0)
    parent_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("email_drafts.id", ondelete="CASCADE")
    )
    unsubscribe_token: Mapped[str] = mapped_column(String(64), unique=True)
    prompt_version: Mapped[str | None] = mapped_column(String(40))
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_message_id: Mapped[str | None] = mapped_column(String(255))


class EmailEvent(UUIDPk, Timestamps, Base):
    __tablename__ = "email_events"

    draft_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("email_drafts.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[EmailEventType] = mapped_column(str_enum(EmailEventType, "email_event_type"))
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SuppressionEntry(UUIDPk, Timestamps, Base):
    """Global do-not-contact list (CAN-SPAM opt-outs, DPDP requests, bounces, manual)."""

    __tablename__ = "suppression_list"
    __table_args__ = (
        CheckConstraint(
            "email IS NOT NULL OR domain IS NOT NULL OR phone_e164 IS NOT NULL", name="has_key"
        ),
    )

    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    domain: Mapped[str | None] = mapped_column(String(255), unique=True)
    phone_e164: Mapped[str | None] = mapped_column(String(20), unique=True)
    reason: Mapped[str] = mapped_column(String(100))
    source: Mapped[str | None] = mapped_column(Text)
