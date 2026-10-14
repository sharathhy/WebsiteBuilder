"""Prometheus-style metrics (admin token required; scrape with a bearer token)."""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select

from leadforge.core.deps import AdminUser, DbSession
from leadforge.models import Business, EmailDraft, GeneratedSite, Job
from leadforge.services.usage import month_spend

router = APIRouter(tags=["ops"])


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics(_: AdminUser, db: DbSession) -> str:
    lines = ["# TYPE leadforge_jobs gauge"]
    for queue, st, n in await db.execute(
        select(Job.queue, Job.status, func.count()).group_by(Job.queue, Job.status)
    ):
        lines.append(f'leadforge_jobs{{queue="{queue.value}",status="{st.value}"}} {n}')
    lines.append("# TYPE leadforge_leads gauge")
    for lead_st, n in await db.execute(
        select(Business.lead_status, func.count()).group_by(Business.lead_status)
    ):
        lines.append(f'leadforge_leads{{status="{lead_st.value}"}} {n}')
    lines.append("# TYPE leadforge_sites gauge")
    for site_st, n in await db.execute(
        select(GeneratedSite.status, func.count()).group_by(GeneratedSite.status)
    ):
        lines.append(f'leadforge_sites{{status="{site_st.value}"}} {n}')
    lines.append("# TYPE leadforge_drafts gauge")
    for draft_st, n in await db.execute(
        select(EmailDraft.status, func.count()).group_by(EmailDraft.status)
    ):
        lines.append(f'leadforge_drafts{{status="{draft_st.value}"}} {n}')
    lines.append("# TYPE leadforge_spend_usd_month gauge")
    lines.append(f"leadforge_spend_usd_month {float(await month_spend(db)):.4f}")
    return "\n".join(lines) + "\n"
