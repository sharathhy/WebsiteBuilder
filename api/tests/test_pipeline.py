"""End to end on mocked APIs: discover -> enrich -> audit -> generate -> gate -> drafts."""

from collections import Counter
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from leadforge.models import Audit, Business, Campaign, EmailDraft, GeneratedSite, Job
from leadforge.models.enums import AuditStatus, DraftStatus, GeneratedSiteStatus, JobStatus
from leadforge.pipeline.runner import InlineDispatcher
from leadforge.services.campaigns import start_campaign
from leadforge.services.container import Services
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
