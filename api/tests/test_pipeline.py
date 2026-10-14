"""End to end on mocked APIs: discover -> enrich -> audit -> generate -> gate -> drafts."""

from collections import Counter
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from leadforge.models import Audit, Business, Campaign, EmailDraft, GeneratedSite, Job, Website
from leadforge.models.enums import (
    AuditStatus,
    DraftStatus,
    GeneratedSiteStatus,
    JobQueue,
    JobStatus,
)
from leadforge.pipeline.runner import InlineDispatcher
from leadforge.services.campaigns import start_campaign
from leadforge.services.container import Services
from leadforge.services.jobs import create_job
from leadforge.services.targets import load_targets


async def run_campaign(
    db: AsyncSession, inline: InlineDispatcher, cities: list[str], max_results: int
) -> Campaign:
    campaign = Campaign(name="test", cities=cities, categories=["dentists"],
                        max_results_per_target=max_results)  # fmt: skip
    db.add(campaign)
    await db.commit()
    await start_campaign(db, campaign, load_targets(), inline)
    await inline.drain()
    return campaign


async def test_bengaluru_and_austin_dentists_end_to_end(
    db: AsyncSession, inline: InlineDispatcher, services: Services
) -> None:
    await run_campaign(db, inline, ["bengaluru", "austin"], 60)

    leads = list(await db.scalars(select(Business).where(Business.duplicate_of_id.is_(None))))
    assert len(leads) >= 50
    # Duplicate branch listings are folded into the original.
    assert await db.scalar(select(func.count()).where(Business.duplicate_of_id.is_not(None)))
    # Fictional fixtures only: nothing that could be mistaken for a real business.
    assert all(b.name.startswith("Sample ") for b in leads)
    assert all(b.domain is None or b.domain.endswith(".example") for b in leads)

    # Every lead got a stored contact status; emails always carry their source page.
    for b in leads:
        assert b.email_status in ("found", "not_found")
        if b.primary_email:
            assert b.email_source_url and b.email_confidence is not None

    # Every lead is scored, apart from bot-walled sites we refuse to bypass.
    statuses = Counter(
        a.status for a in await db.scalars(select(Audit).where(Audit.generated_site_id.is_(None)))
    )
    unscored = [b for b in leads if b.latest_score is None]
    assert statuses[AuditStatus.FAILED] == len(unscored)
    assert {b.latest_grade for b in leads if b.latest_score is not None} <= {"A", "B", "C", "D"}

    # Every lead under the threshold got a preview that passed the quality gate.
    low = [b for b in leads if b.latest_score is not None and b.latest_score < 60]
    assert low, "fixtures should produce rebuild candidates"
    sites = {s.business_id: s for s in await db.scalars(select(GeneratedSite))}
    for b in low:
        site = sites[b.id]
        assert site.status == GeneratedSiteStatus.LIVE, site.failure_reason
        assert site.score is not None and site.score >= 90
        assert site.score >= (site.baseline_score or 0) + 30
        assert site.preview_url and site.noindex

    # Page parity: every page of the current site answers on the preview.
    websites = {w.business_id: w for w in await db.scalars(select(Website))}
    checked = 0
    for b in low:
        site, web = sites[b.id], websites.get(b.id)
        if web is None or not web.page_inventory:
            continue
        parity = site.page_parity
        assert parity and parity["missing"] == [], parity
        assert parity["expected"] == len(web.page_inventory) > 3
        spec_paths = {p["path"] for p in site.site_spec["pages"]}
        for page in web.page_inventory:
            if page["kind"] not in ("home", "privacy"):
                assert page["path"].removesuffix(".html") in spec_paths
        checked += 1
    assert checked, "fixtures should include multi-page sites to rebuild"

    # Outreach is drafted, never sent.
    drafts = list(await db.scalars(select(EmailDraft)))
    assert drafts and all(d.status == DraftStatus.DRAFTED for d in drafts)
    assert not (Path(services.settings.storage_dir) / "outbox").exists()
    for d in drafts:
        if d.channel.value == "email":
            assert "/u/" in d.body  # one-click unsubscribe link in every email
            assert len(d.body.split()) <= 260

    # Nothing dead-lettered.
    dead = await db.scalar(select(func.count()).where(Job.status == JobStatus.DEAD))
    assert dead == 0


async def test_rerunning_a_campaign_is_idempotent(
    db: AsyncSession, inline: InlineDispatcher
) -> None:
    await run_campaign(db, inline, ["austin"], 5)
    first = await db.scalar(select(func.count()).select_from(Business))
    sites = await db.scalar(select(func.count()).select_from(GeneratedSite))
    await run_campaign(db, inline, ["austin"], 5)
    assert await db.scalar(select(func.count()).select_from(Business)) == first
    assert await db.scalar(select(func.count()).select_from(GeneratedSite)) == sites


async def test_regenerate_backfills_the_page_list(
    db: AsyncSession, inline: InlineDispatcher, services: Services
) -> None:
    """Leads crawled before page parity existed get their page list on the next build."""
    await run_campaign(db, inline, ["austin"], 20)
    site = await db.scalar(
        select(GeneratedSite)
        .join(Website, Website.business_id == GeneratedSite.business_id)
        .where(GeneratedSite.status == GeneratedSiteStatus.LIVE)
        .limit(1)
    )
    assert site is not None
    site_id, biz_id = site.id, site.business_id
    web = await db.scalar(select(Website).where(Website.business_id == biz_id))
    assert web is not None and len(web.page_inventory) > 3
    expected = [p["path"] for p in web.page_inventory]
    web.page_inventory = []
    await db.commit()

    job, _ = await create_job(
        db, queue=JobQueue.GENERATE, kind="generate", business_id=biz_id,
        payload={"force": True}, idempotency_key="generate:backfill",
    )  # fmt: skip
    await inline.dispatch(job)
    await inline.drain()
    db.expire_all()
    web = await db.scalar(select(Website).where(Website.business_id == biz_id))
    assert web is not None and [p["path"] for p in web.page_inventory] == expected
    newest = await db.scalar(
        select(GeneratedSite)
        .where(GeneratedSite.business_id == biz_id)
        .order_by(GeneratedSite.created_at.desc())
        .limit(1)
    )
    assert newest is not None and newest.id != site_id
    assert newest.page_parity and newest.page_parity["missing"] == []
    assert newest.page_parity["expected"] == len(expected)
