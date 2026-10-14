import csv
import io
import re
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from openpyxl import Workbook
from sqlalchemy import func, select

from leadforge.core.deps import CurrentUser, DbSession
from leadforge.core.dispatch import JobDispatcher
from leadforge.models import (
    Audit,
    Business,
    Contact,
    EmailDraft,
    GeneratedSite,
    Job,
    Screenshot,
    Website,
)
from leadforge.models.enums import JobQueue, LeadStatus
from leadforge.schemas.jobs import JobOut
from leadforge.schemas.leads import LeadDetail, LeadPage, SiteOut
from leadforge.services import leads as lq
from leadforge.services.jobs import create_job
from leadforge.services.storage import get_storage

router = APIRouter(prefix="/leads", tags=["leads"])


def _filters(
    campaign_id: uuid.UUID | None = None,
    city: str | None = None,
    category: str | None = None,
    country: str | None = Query(None, pattern="^(IN|US)$"),
    grade: str | None = Query(None, pattern="^[ABCD]$"),
    min_score: int | None = Query(None, ge=0, le=100),
    max_score: int | None = Query(None, ge=0, le=100),
    has_website: bool | None = None,
    email: Literal["found", "not_found"] | None = None,
    status: LeadStatus | None = None,
    q: str | None = Query(None, max_length=100),
) -> dict[str, Any]:
    return dict(
        campaign_id=campaign_id, city=city, category=category, country=country, grade=grade,
        min_score=min_score, max_score=max_score, has_website=has_website, email=email,
        status=status, q=q,
    )  # fmt: skip


Filters = Annotated[dict[str, Any], Depends(_filters)]
PHONE_LIKE = re.compile(r"[+-][\d\s().-]+")


@router.get("", response_model=LeadPage)
async def list_leads(
    _: CurrentUser,
    db: DbSession,
    filters: Filters,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort: str = Query("score", pattern="^(-?score|name|-created|rating)$"),
) -> LeadPage:
    stmt = lq.lead_query(**filters)
    total = int(await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        await db.scalars(
            stmt.order_by(lq.SORTS[sort], Business.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    previews = await lq.latest_previews(db, [b.id for b in rows])
    return LeadPage(
        items=[lq.to_row(b, previews.get(b.id)) for b in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/export")
async def export_leads(
    _: CurrentUser,
    db: DbSession,
    filters: Filters,
    format: Literal["csv", "xlsx"] = "csv",
) -> Response:
    """Export the filtered lead list. Missing values say "not found"; nothing is guessed."""
    rows = list(await db.scalars(lq.lead_query(**filters).order_by(lq.SORTS["score"])))
    previews = await lq.latest_previews(db, [b.id for b in rows])
    records = [lq.export_record(lq.to_row(b, previews.get(b.id))) for b in rows]
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
    if format == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=lq.EXPORT_COLUMNS)
        writer.writeheader()
        for r in records:
            writer.writerow({k: _csv_safe(v) for k, v in r.items()})
        return Response(
            buf.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="leads-{stamp}.csv"'},
        )
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Leads"
    ws.append(lq.EXPORT_COLUMNS)
    for r in records:
        ws.append([_csv_safe(r[k]) for k in lq.EXPORT_COLUMNS])
    ws.freeze_panes = "A2"
    out = io.BytesIO()
    wb.save(out)
    return Response(
        out.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="leads-{stamp}.xlsx"'},
    )


def _csv_safe(value: Any) -> Any:
    """Neutralise spreadsheet formula injection from scraped text."""
    if isinstance(value, str) and (
        value[:1] in ("=", "@", "\t", "\r")
        or (value[:1] in ("+", "-") and not PHONE_LIKE.fullmatch(value))
    ):
        return "'" + value
    return value


async def _business(db: DbSession, lead_id: uuid.UUID) -> Business:
    biz = await db.get(Business, lead_id)
    if biz is None:
        raise HTTPException(404, "Lead not found")
    return biz


@router.get("/{lead_id}", response_model=LeadDetail)
async def lead_detail(lead_id: uuid.UUID, _: CurrentUser, db: DbSession) -> LeadDetail:
    biz = await _business(db, lead_id)
    storage = get_storage()
    previews = await lq.latest_previews(db, [biz.id])
    contacts = list(await db.scalars(select(Contact).where(Contact.business_id == biz.id)))
    website = await db.scalar(select(Website).where(Website.business_id == biz.id))
    audits = list(
        await db.scalars(
            select(Audit).where(Audit.business_id == biz.id).order_by(Audit.created_at.desc())
        )
    )
    shots: dict[uuid.UUID, list[Screenshot]] = {}
    if audits:
        for s in await db.scalars(
            select(Screenshot).where(Screenshot.audit_id.in_([a.id for a in audits]))
        ):
            shots.setdefault(s.audit_id, []).append(s)
    sites = list(
        await db.scalars(
            select(GeneratedSite)
            .where(GeneratedSite.business_id == biz.id)
            .order_by(GeneratedSite.created_at.desc())
        )
    )
    by_id = {s.id: s for s in sites}
    drafts = list(
        await db.scalars(
            select(EmailDraft)
            .where(EmailDraft.business_id == biz.id)
            .order_by(EmailDraft.sequence_day, EmailDraft.variant, EmailDraft.created_at)
        )
    )
    jobs = list(
        await db.scalars(
            select(Job).where(Job.business_id == biz.id).order_by(Job.created_at.desc()).limit(50)
        )
    )
    return LeadDetail(
        lead=lq.to_row(biz, previews.get(biz.id)),
        business={
            "place_id": biz.place_id,
            "primary_type": biz.primary_type,
            "hours": biz.hours,
            "lat": biz.lat,
            "lng": biz.lng,
            "business_status": biz.business_status,
            "phone_national": biz.phone_national,
            "domain": biz.domain,
            "duplicate_of_id": str(biz.duplicate_of_id) if biz.duplicate_of_id else None,
        },
        contacts=[
            {
                "id": str(c.id),
                "kind": c.kind.value,
                "value": c.value,
                "label": c.label,
                "source": c.source.value,
                "source_url": c.source_url,
                "confidence": c.confidence,
                "is_role_address": c.is_role_address,
                "mx_valid": c.mx_valid,
                "found_at": c.found_at,
            }
            for c in contacts
        ],
        website=None
        if website is None
        else {
            "url": website.url,
            "final_url": website.final_url,
            "status": website.status.value,
            "http_status": website.http_status,
            "is_https": website.is_https,
            "robots_allowed": website.robots_allowed,
            "tech_stack": website.tech_stack,
            "pages_crawled": website.pages_crawled,
            "last_crawled_at": website.last_crawled_at,
        },
        audits=[
            {
                "id": str(a.id),
                "target_url": a.target_url,
                "status": a.status.value,
                "score": a.total_score,
                "grade": a.grade.value if a.grade else None,
                "rubric_version": a.rubric_version,
                "breakdown": a.breakdown,
                "top_issues": a.top_issues,
                "error": a.error,
                "created_at": a.created_at,
                "generated_site_id": str(a.generated_site_id) if a.generated_site_id else None,
                "evidence": a.evidence,
                "screenshots": {
                    s.viewport.value: storage.url(s.storage_key) for s in shots.get(a.id, [])
                },
            }
            for a in audits
        ],
        sites=[SiteOut.model_validate(s) for s in sites],
        drafts=[
            lq.draft_out(d, biz, by_id.get(d.generated_site_id) if d.generated_site_id else None)
            for d in drafts
        ],
        jobs=[JobOut.model_validate(j).model_dump(mode="json") for j in jobs],
    )


@router.post("/{lead_id}/reaudit", response_model=JobOut, status_code=202)
async def reaudit(
    lead_id: uuid.UUID, _: CurrentUser, db: DbSession, dispatcher: JobDispatcher
) -> Job:
    biz = await _business(db, lead_id)
    job, created = await create_job(
        db, queue=JobQueue.AUDIT, kind="audit", business_id=biz.id, payload={"force": True},
        idempotency_key=f"audit:{biz.id}:manual:{uuid.uuid4().hex[:8]}",
    )  # fmt: skip
    if created:
        await dispatcher.dispatch(job)
    return job


@router.post("/{lead_id}/regenerate", response_model=JobOut, status_code=202)
async def regenerate(
    lead_id: uuid.UUID, _: CurrentUser, db: DbSession, dispatcher: JobDispatcher
) -> Job:
    biz = await _business(db, lead_id)
    job, created = await create_job(
        db, queue=JobQueue.GENERATE, kind="generate", business_id=biz.id,
        payload={"business_id": str(biz.id), "force": True},
        idempotency_key=f"generate:{biz.id}:manual:{uuid.uuid4().hex[:8]}",
    )  # fmt: skip
    if created:
        await dispatcher.dispatch(job)
    return job
