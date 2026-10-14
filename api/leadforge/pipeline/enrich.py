"""Enrich: crawl the business site (max ~10 pages) for public contact details."""

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

from sqlalchemy import select

from leadforge.models import Business, Contact, Website
from leadforge.models.enums import (
    ContactKind,
    ContactSource,
    JobQueue,
    LeadStatus,
    WebsiteStatus,
)
from leadforge.pipeline.context import JobContext
from leadforge.pipeline.registry import PermanentError, handler
from leadforge.services import contacts as cx
from leadforge.services.dedup import domain_of

NOT_FOUND = "not_found"


async def _upsert_contact(ctx: JobContext, biz: Business, c: cx.FoundContact) -> None:
    existing = await ctx.db.scalar(
        select(Contact).where(
            Contact.business_id == biz.id, Contact.kind == c.kind, Contact.value == c.value
        )
    )
    row = existing or Contact(business_id=biz.id, kind=c.kind, value=c.value, source=c.source)
    row.source = c.source
    row.source_url = c.source_url
    row.label = c.label
    row.confidence = c.confidence
    row.is_role_address = c.is_role_address
    row.mx_valid = c.mx_valid
    row.is_disposable = c.is_disposable
    row.found_at = datetime.now(UTC)
    if existing is None:
        ctx.db.add(row)


async def crawl(ctx: JobContext, biz: Business, site: Website) -> list[cx.FoundContact]:
    fetcher = ctx.services.fetcher
    settings = ctx.services.settings
    found: list[cx.FoundContact] = []
    home = await fetcher.get(site.url)
    site.last_crawled_at = datetime.now(UTC)
    site.robots_allowed = home.error != "blocked_by_robots"
    site.crawl_delay_s = fetcher.crawl_delay(site.url)
    site.http_status = home.status or None
    site.final_url = home.final_url
    site.is_https = home.final_url.startswith("https://")
    if home.error == "blocked_by_robots":
        site.status = WebsiteStatus.BLOCKED_BY_ROBOTS
        return found
    if home.error == "timeout":
        site.status = WebsiteStatus.TIMEOUT
        return found
    if home.error:
        site.status = WebsiteStatus.UNREACHABLE
        return found
    if home.is_challenge:
        site.status = WebsiteStatus.CHALLENGE
        return found
    if home.is_parked:
        site.status = WebsiteStatus.PARKED
        return found
    if not home.ok:
        site.status = WebsiteStatus.UNREACHABLE
        return found
    site.status = WebsiteStatus.OK

    pages = [home]
    for url in cx.candidate_pages(home.text, home.final_url):
        if len(pages) >= settings.crawler_max_pages:
            break
        res = await fetcher.get(url)
        if res.ok and "text/html" in res.headers.get("content-type", "text/html"):
            pages.append(res)
    site.pages_crawled = [p.final_url for p in pages]
    for page in pages:
        found += cx.extract_emails(page.text, page.final_url)
        found += cx.extract_phones(page.text, page.final_url, biz.country)
        found += cx.extract_links(page.text, page.final_url)
    return found


@handler("enrich")
async def enrich(ctx: JobContext) -> dict[str, Any]:
    biz = await ctx.db.get(Business, ctx.job.business_id)
    if biz is None:
        raise PermanentError("business not found")

    found: list[cx.FoundContact] = []
    if biz.phone_e164:
        found.append(
            cx.FoundContact(
                ContactKind.PHONE,
                biz.phone_e164,
                ContactSource.PLACES,
                biz.google_maps_url or "",
                label="google",
                confidence=0.95,
            )
        )

    site: Website | None = None
    if biz.website:
        site = await ctx.db.scalar(select(Website).where(Website.business_id == biz.id))
        if site is None:
            url = biz.website if "://" in biz.website else f"http://{biz.website}"
            site = Website(business_id=biz.id, url=urljoin(url, "/"), domain=domain_of(url) or "")
            ctx.db.add(site)
            await ctx.db.flush()
        found += await crawl(ctx, biz, site)

    # Dedup within this crawl and validate emails.
    unique: dict[tuple[str, str], cx.FoundContact] = {}
    for c in found:
        unique.setdefault((c.kind.value, c.value), c)
    contacts = list(unique.values())
    for c in contacts:
        if c.kind == ContactKind.EMAIL:
            await cx.validate_email(c, biz.domain, ctx.services.mx_resolver)
        elif c.kind == ContactKind.PHONE and not c.confidence:
            c.confidence = 0.8
        await _upsert_contact(ctx, biz, c)

    best = cx.best_email(contacts)
    if best is not None and best.confidence >= 0.3:
        biz.primary_email = best.value
        biz.email_status = "found"
        biz.email_confidence = best.confidence
        biz.email_source_url = best.source_url
    else:
        biz.primary_email = None
        biz.email_status = NOT_FOUND
        biz.email_confidence = None
        biz.email_source_url = site.final_url if site else None
    biz.enriched_at = datetime.now(UTC)
    biz.lead_status = LeadStatus.ENRICHED
    await ctx.db.commit()

    await ctx.enqueue(
        JobQueue.AUDIT,
        "audit",
        f"audit:{biz.id}:{ctx.job.campaign_id}",
        {"business_id": str(biz.id)},
        business_id=biz.id,
    )
    return {
        "website_status": site.status.value if site else "none",
        "emails": sum(1 for c in contacts if c.kind == ContactKind.EMAIL),
        "phones": sum(1 for c in contacts if c.kind == ContactKind.PHONE),
        "primary_email": biz.primary_email or NOT_FOUND,
    }
