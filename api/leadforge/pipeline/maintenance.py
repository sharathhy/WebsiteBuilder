"""Scheduled maintenance: expire previews, re-audit stale leads, refresh Places data."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from leadforge.models import Business, GeneratedSite
from leadforge.models.enums import GeneratedSiteStatus, JobQueue, LeadStatus
from leadforge.pipeline.context import JobContext
from leadforge.pipeline.registry import handler
from leadforge.services.targets import load_targets


@handler("expire_previews")
async def expire_previews(ctx: JobContext) -> dict[str, Any]:
    now = datetime.now(UTC)
    sites = list(
        await ctx.db.scalars(
            select(GeneratedSite).where(
                GeneratedSite.status == GeneratedSiteStatus.LIVE,
                GeneratedSite.expires_at.is_not(None),
            )
        )
    )
    expired = 0
    for site in sites:
        assert site.expires_at is not None
        exp = site.expires_at if site.expires_at.tzinfo else site.expires_at.replace(tzinfo=UTC)
        if exp <= now:
            slug = (site.preview_url or "").rstrip("/").rsplit("/", 1)[-1].split(".")[0]
            await ctx.services.deployer.remove(slug, site.vercel_project_id)
            site.status = GeneratedSiteStatus.EXPIRED
            expired += 1
    await ctx.db.commit()
    return {"expired": expired}


@handler("reaudit_stale")
async def reaudit_stale(ctx: JobContext) -> dict[str, Any]:
    days = load_targets().defaults.audit_cache_days
    cutoff = datetime.now(UTC) - timedelta(days=days)
    stale = list(
        await ctx.db.scalars(
            select(Business.id)
            .where(
                Business.audited_at < cutoff,
                Business.duplicate_of_id.is_(None),
                Business.lead_status.not_in([LeadStatus.SUPPRESSED, LeadStatus.WON]),
            )
            .limit(500)
        )
    )
    stamp = datetime.now(UTC).strftime("%Y%m")
    for biz_id in stale:
        await ctx.enqueue(
            JobQueue.AUDIT,
            "audit",
            f"reaudit:{biz_id}:{stamp}",
            {"business_id": str(biz_id), "force": True},
            business_id=biz_id,
        )
    return {"queued": len(stale)}


@handler("refresh_places")
async def refresh_places(ctx: JobContext) -> dict[str, Any]:
    """Google caching terms: Places content is refreshed periodically (place_id is kept)."""
    days = load_targets().defaults.places_refresh_days
    cutoff = datetime.now(UTC) - timedelta(days=days)
    count = await ctx.db.scalar(
        select(Business.id).where(Business.places_fetched_at < cutoff).limit(1)
    )
    # Re-running a campaign's discover jobs refreshes rows in place; flag here for the dashboard.
    return {"stale_places": bool(count)}
