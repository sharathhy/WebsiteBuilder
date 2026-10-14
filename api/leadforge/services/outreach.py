"""Outreach drafting and compliance: A/B subjects, <=150-word bodies, CAN-SPAM footer,
one-click unsubscribe, suppression checks and daily throttling."""

import secrets
from datetime import UTC, datetime

from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from leadforge.core.config import Settings
from leadforge.models import Business, EmailDraft, SuppressionEntry
from leadforge.models.enums import DraftStatus, OutreachChannel
from leadforge.services.agency import AgencyConfig

MAX_BODY_WORDS = 150


class EmailCopy(BaseModel):
    subject_a: str = Field(max_length=90)
    subject_b: str = Field(max_length=90)
    body: str


class ShortMessage(BaseModel):
    text: str


def word_count(text: str) -> int:
    return len(text.split())


def price_hint(agency: AgencyConfig, country: str) -> str:
    book = agency.pricing.get(country) or agency.pricing.get("US")
    if book is None:
        return ""
    starter = min(book.tiers.values())
    if book.currency == "INR":
        return f"{book.symbol}{starter:,.0f}".replace(",", ",")
    return f"{book.symbol}{starter:,}"


def mock_email(facts: dict[str, object], agency: AgencyConfig) -> EmailCopy:
    issues = [str(i) for i in facts.get("issues", [])][:3]  # type: ignore[attr-defined]
    issue_lines = "\n".join(f"- {i}" for i in issues) or "- Customers can't find you online"
    name = facts["business_name"]
    old, new = facts["score_before"], facts["score_after"]
    body = (
        f"Hi {name} team,\n\n"
        f"I run a small web studio and looked at how {name} shows up online. "
        f"A few things stood out:\n{issue_lines}\n\n"
        f"So I built a free preview of a new mobile-first site for you. It scores "
        f"{new}/100 on our audit, up from {old}:\n{facts['preview_url']}\n\n"
        f"If you like it, sites like this start at {facts['price_from']}. "
        "Just reply to this email and I'll answer any questions.\n\n"
        f"{agency.sender_name}, {agency.agency_name}"
    )
    subject_a = f"Quick idea for {name}'s website (score {old} → {new})"
    subject_b = f"I made {name} a free website preview"
    return EmailCopy(subject_a=subject_a[:90], subject_b=subject_b[:90], body=body)


FOOTER_MARK = "\n\n--\n"


def compliance_footer(agency: AgencyConfig, unsubscribe_url: str) -> str:
    return (
        FOOTER_MARK + f"{agency.agency_name}, {agency.physical_address}\n"
        "You're receiving this one-off note because your business contact details are "
        "published online. Not interested? Unsubscribe in one click and we won't contact "
        f"you again: {unsubscribe_url}"
    )


def with_footer(body: str, agency: AgencyConfig, unsubscribe_url: str) -> str:
    """Replace any existing footer with a fresh one, so the address and opt-out link are
    always current (and can't be edited away) when the message actually goes out."""
    main = body.split(FOOTER_MARK, 1)[0].rstrip()
    return main + compliance_footer(agency, unsubscribe_url)


def unsubscribe_url(settings: Settings, token: str) -> str:
    return f"{settings.public_base_url.rstrip('/')}/u/{token}"


def new_token() -> str:
    return secrets.token_urlsafe(24)


async def is_suppressed(db: AsyncSession, biz: Business, email: str | None) -> bool:
    conds = []
    if email:
        conds.append(SuppressionEntry.email == email.lower())
        conds.append(SuppressionEntry.domain == email.split("@")[-1].lower())
    if biz.domain:
        conds.append(SuppressionEntry.domain == biz.domain)
    if biz.phone_e164:
        conds.append(SuppressionEntry.phone_e164 == biz.phone_e164)
    if not conds:
        return False
    return bool(
        await db.scalar(select(func.count()).select_from(SuppressionEntry).where(or_(*conds)))
    )


async def sent_today(db: AsyncSession) -> int:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return int(
        await db.scalar(
            select(func.count())
            .select_from(EmailDraft)
            .where(
                EmailDraft.channel == OutreachChannel.EMAIL,
                EmailDraft.sent_at >= start,
            )
        )
        or 0
    )


async def cancel_pending(db: AsyncSession, business_id: object, reason: str) -> int:
    drafts = list(
        await db.scalars(
            select(EmailDraft).where(
                EmailDraft.business_id == business_id,
                EmailDraft.status.in_([DraftStatus.DRAFTED, DraftStatus.APPROVED]),
            )
        )
    )
    for d in drafts:
        d.status = DraftStatus.CANCELLED
        d.provider_message_id = d.provider_message_id or f"cancelled:{reason}"
    return len(drafts)
