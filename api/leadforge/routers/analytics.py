"""Funnel, spend vs budget, and queue health for the dashboard."""

from typing import Any

from fastapi import APIRouter
from sqlalchemy import func, select

from leadforge.core.config import get_settings
from leadforge.core.deps import CurrentUser, DbSession
from leadforge.models import ApiUsage, Business, EmailDraft, EmailEvent, GeneratedSite, Job
from leadforge.models.enums import (
    DraftStatus,
    EmailEventType,
    GeneratedSiteStatus,
    JobStatus,
    LeadStatus,
)
from leadforge.services.agency import load_agency
from leadforge.services.usage import FREE_QUOTAS, month_start

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def overview(_: CurrentUser, db: DbSession) -> dict[str, Any]:
    live = Business.duplicate_of_id.is_(None)
    leads = {
        st.value: n
        for st, n in await db.execute(
            select(Business.lead_status, func.count()).where(live).group_by(Business.lead_status)
        )
    }
    total = sum(leads.values())
    audited = int(
        await db.scalar(select(func.count()).where(live, Business.latest_score.is_not(None))) or 0
    )
    threshold_hits = int(
        await db.scalar(select(func.count()).where(live, Business.latest_score < 60)) or 0
    )
    sites = {
        st.value: n
        for st, n in await db.execute(
            select(GeneratedSite.status, func.count()).group_by(GeneratedSite.status)
        )
    }
    drafts = {
        st.value: n
        for st, n in await db.execute(
            select(EmailDraft.status, func.count()).group_by(EmailDraft.status)
        )
    }
    events = {
        t.value: n
        for t, n in await db.execute(
            select(EmailEvent.type, func.count()).group_by(EmailEvent.type)
        )
    }
    grades = {
        g: n
        for g, n in await db.execute(
            select(Business.latest_grade, func.count())
            .where(live, Business.latest_grade.is_not(None))
            .group_by(Business.latest_grade)
        )
    }
    avg = (
        await db.execute(
            select(func.avg(GeneratedSite.baseline_score), func.avg(GeneratedSite.score)).where(
                GeneratedSite.status == GeneratedSiteStatus.LIVE
            )
        )
    ).one()
    with_email = int(
        await db.scalar(select(func.count()).where(live, Business.primary_email.is_not(None))) or 0
    )

    def n(*statuses: DraftStatus) -> int:
        return sum(drafts.get(s.value, 0) for s in statuses)

    funnel = [
        {"stage": "Discovered", "count": total},
        {"stage": "Audited", "count": audited},
        {"stage": "Below 60", "count": threshold_hits},
        {"stage": "Preview live", "count": sites.get(GeneratedSiteStatus.LIVE.value, 0)},
        {"stage": "Approved", "count": n(DraftStatus.APPROVED, DraftStatus.SENT, DraftStatus.REPLIED, DraftStatus.WON, DraftStatus.LOST)},
        {"stage": "Sent", "count": n(DraftStatus.SENT, DraftStatus.REPLIED, DraftStatus.WON, DraftStatus.LOST)},
        {"stage": "Replied", "count": n(DraftStatus.REPLIED, DraftStatus.WON, DraftStatus.LOST)},
        {"stage": "Won", "count": leads.get(LeadStatus.WON.value, 0)},
    ]  # fmt: skip
    return {
        "funnel": funnel,
        "leads_by_status": leads,
        "grades": grades,
        "sites_by_status": sites,
        "drafts_by_status": drafts,
        "email_events": events,
        "emails_found": with_email,
        "bounces": events.get(EmailEventType.BOUNCED.value, 0),
        "avg_score_before": round(float(avg[0]), 1) if avg[0] is not None else None,
        "avg_score_after": round(float(avg[1]), 1) if avg[1] is not None else None,
    }


@router.get("/costs")
async def costs(_: CurrentUser, db: DbSession) -> dict[str, Any]:
    agency = load_agency()
    rows = await db.execute(
        select(
            ApiUsage.provider,
            ApiUsage.mocked,
            func.count(),
            func.coalesce(func.sum(ApiUsage.units), 0),
            func.coalesce(func.sum(ApiUsage.cost_usd), 0),
            func.coalesce(func.sum(ApiUsage.tokens_in), 0),
            func.coalesce(func.sum(ApiUsage.tokens_out), 0),
        )
        .where(ApiUsage.created_at >= month_start())
        .group_by(ApiUsage.provider, ApiUsage.mocked)
    )
    providers: dict[str, dict[str, Any]] = {}
    spent = 0.0
    for provider, mocked, calls, units, cost, tin, tout in rows:
        p = providers.setdefault(
            provider.value,
            {"calls": 0, "mocked_calls": 0, "units": 0, "cost_usd": 0.0, "tokens_in": 0,
             "tokens_out": 0, "budget_usd": agency.provider_budgets_usd.get(provider.value),
             "free_quota": FREE_QUOTAS.get(provider)},
        )  # fmt: skip
        key = "mocked_calls" if mocked else "calls"
        p[key] += calls
        p["units"] += int(units or 0)
        p["tokens_in"] += int(tin or 0)
        p["tokens_out"] += int(tout or 0)
        if not mocked:
            p["cost_usd"] = round(p["cost_usd"] + float(cost), 4)
            spent += float(cost)
    return {
        "month_start": month_start().isoformat(),
        "budget_usd": agency.monthly_budget_usd,
        "spent_usd": round(spent, 4),
        "remaining_usd": round(max(agency.monthly_budget_usd - spent, 0), 4),
        "mock_mode": get_settings().mock_apis,
        "providers": providers,
    }


@router.get("/queues")
async def queues(_: CurrentUser, db: DbSession) -> dict[str, Any]:
    counts: dict[str, dict[str, int]] = {}
    for queue, st, n in await db.execute(
        select(Job.queue, Job.status, func.count()).group_by(Job.queue, Job.status)
    ):
        counts.setdefault(queue.value, {})[st.value] = n
    dead = list(
        await db.scalars(
            select(Job)
            .where(Job.status == JobStatus.DEAD)
            .order_by(Job.finished_at.desc())
            .limit(50)
        )
    )
    durations: dict[str, list[float]] = {}
    for kind, started, finished in await db.execute(
        select(Job.kind, Job.started_at, Job.finished_at)
        .where(Job.status == JobStatus.SUCCEEDED, Job.started_at.is_not(None))
        .order_by(Job.finished_at.desc())
        .limit(1000)
    ):
        if finished is not None and started is not None:
            durations.setdefault(kind, []).append((finished - started).total_seconds())
    avg = {k: round(sum(v) / len(v), 2) for k, v in durations.items()}
    return {
        "counts": counts,
        "avg_duration_s": avg,
        "dead_letters": [
            {
                "id": str(j.id),
                "kind": j.kind,
                "queue": j.queue.value,
                "error": j.error,
                "attempts": j.attempts,
                "finished_at": j.finished_at,
                "business_id": str(j.business_id) if j.business_id else None,
            }
            for j in dead
        ],
    }
