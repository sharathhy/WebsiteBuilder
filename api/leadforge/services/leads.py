"""Lead queries shared by the leads API and exports."""

import uuid
from typing import Any

from sqlalchemy import Select, String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from leadforge.models import Business, EmailDraft, GeneratedSite, campaign_businesses
from leadforge.models.enums import GeneratedSiteStatus, LeadStatus
from leadforge.schemas.leads import NOT_FOUND, DraftOut, LeadRow

SORTS: dict[str, Any] = {
    "score": Business.latest_score.asc().nulls_last(),
    "-score": Business.latest_score.desc().nulls_last(),
    "name": Business.name.asc(),
    "-created": Business.created_at.desc(),
    "rating": Business.rating.desc().nulls_last(),
}


def lead_query(
    *,
    campaign_id: uuid.UUID | None = None,
    city: str | None = None,
    category: str | None = None,
    country: str | None = None,
    grade: str | None = None,
    min_score: int | None = None,
    max_score: int | None = None,
    has_website: bool | None = None,
    email: str | None = None,
    status: LeadStatus | None = None,
    q: str | None = None,
    include_duplicates: bool = False,
) -> Select[Any]:
    stmt = select(Business)
    if not include_duplicates:
        stmt = stmt.where(Business.duplicate_of_id.is_(None))
    if campaign_id:
        stmt = stmt.join(
            campaign_businesses, campaign_businesses.c.business_id == Business.id
        ).where(campaign_businesses.c.campaign_id == campaign_id)
    if city:
        stmt = stmt.where(Business.city == city)
    if category:
        stmt = stmt.where(Business.category == category)
    if country:
        stmt = stmt.where(Business.country == country)
    if grade:
        stmt = stmt.where(Business.latest_grade == grade)
    if min_score is not None:
        stmt = stmt.where(Business.latest_score >= min_score)
    if max_score is not None:
        stmt = stmt.where(Business.latest_score <= max_score)
    if has_website is not None:
        stmt = stmt.where(Business.has_website.is_(has_website))
    if email == "found":
        stmt = stmt.where(Business.primary_email.is_not(None))
    elif email == "not_found":
        stmt = stmt.where(Business.primary_email.is_(None))
    if status:
        stmt = stmt.where(Business.lead_status == status)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Business.name).like(like),
                func.lower(Business.address).like(like),
                func.lower(cast(Business.primary_email, String)).like(like),
            )
        )
    return stmt


async def latest_previews(db: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not ids:
        return {}
    rows = await db.execute(
        select(GeneratedSite.business_id, GeneratedSite.preview_url)
        .where(GeneratedSite.business_id.in_(ids), GeneratedSite.status == GeneratedSiteStatus.LIVE)
        .order_by(GeneratedSite.created_at)
    )
    return {bid: url for bid, url in rows if url}


def to_row(b: Business, preview: str | None) -> LeadRow:
    return LeadRow(
        id=b.id, name=b.name, category=b.category, city=b.city, state=b.state,
        country=b.country, address=b.address or NOT_FOUND,
        phone=b.phone_e164 or NOT_FOUND,
        email=b.primary_email or (NOT_FOUND if b.email_status == "not_found" else "pending"),
        email_source_url=b.email_source_url, email_confidence=b.email_confidence,
        website=b.website or NOT_FOUND, maps_url=b.google_maps_url, rating=b.rating,
        review_count=b.review_count, score=b.latest_score, grade=b.latest_grade,
        lead_status=b.lead_status, has_website=b.has_website, preview_url=preview,
        places_fetched_at=b.places_fetched_at, enriched_at=b.enriched_at,
        audited_at=b.audited_at,
    )  # fmt: skip


EXPORT_COLUMNS = [
    "name", "category", "email", "email_confidence", "email_source_url", "phone", "address",
    "city", "state", "country", "website", "maps_url", "rating", "review_count", "score",
    "grade", "lead_status", "preview_url", "places_fetched_at", "enriched_at", "audited_at",
]  # fmt: skip


def export_record(row: LeadRow) -> dict[str, Any]:
    data = row.model_dump(mode="json")
    return {k: data.get(k) for k in EXPORT_COLUMNS}


def draft_out(d: EmailDraft, biz: Business, site: GeneratedSite | None) -> DraftOut:
    out = DraftOut.model_validate(d)
    out.business_name = biz.name
    out.to = biz.primary_email if d.channel.value == "email" else biz.phone_e164
    if site:
        out.preview_url, out.score_after, out.score_before = (
            site.preview_url, site.score, site.baseline_score,
        )  # fmt: skip
    return out
