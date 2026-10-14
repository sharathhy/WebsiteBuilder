"""Do-not-contact list writes. Idempotent: suppressing twice is harmless."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from leadforge.models import SuppressionEntry


async def suppress(
    db: AsyncSession,
    *,
    reason: str,
    email: str | None = None,
    domain: str | None = None,
    phone_e164: str | None = None,
    source: str | None = None,
) -> SuppressionEntry:
    email = email.strip().lower() if email else None
    domain = domain.strip().lower().removeprefix("www.") if domain else None
    if not (email or domain or phone_e164):
        raise ValueError("need an email, domain or phone")
    for col, value in (
        (SuppressionEntry.email, email),
        (SuppressionEntry.domain, domain),
        (SuppressionEntry.phone_e164, phone_e164),
    ):
        if value and (found := await db.scalar(select(SuppressionEntry).where(col == value))):
            return found
    entry = SuppressionEntry(
        email=email, domain=domain, phone_e164=phone_e164, reason=reason, source=source
    )
    db.add(entry)
    await db.flush()
    return entry
