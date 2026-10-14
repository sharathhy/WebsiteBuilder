"""The approval queue. Every outbound message needs a signed-in human to approve it."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from leadforge.core.config import get_settings
from leadforge.core.deps import CurrentUser, DbSession
from leadforge.core.dispatch import OptionalDispatcher
from leadforge.models import Business, EmailDraft, GeneratedSite
from leadforge.models.enums import DraftStatus, JobQueue, LeadStatus, OutreachChannel
from leadforge.schemas.leads import ApproveIn, DraftEdit, DraftOut, MarkIn
from leadforge.services import outreach as ox
from leadforge.services.agency import load_agency
from leadforge.services.jobs import create_job
from leadforge.services.leads import draft_out

router = APIRouter(prefix="/drafts", tags=["outreach"])

OPEN = (DraftStatus.DRAFTED, DraftStatus.APPROVED)
OUTCOMES = {
    DraftStatus.REPLIED: None,
    DraftStatus.WON: LeadStatus.WON,
    DraftStatus.LOST: LeadStatus.LOST,
}


async def _load(db: DbSession, draft_id: uuid.UUID) -> tuple[EmailDraft, Business]:
    draft = await db.get(EmailDraft, draft_id)
    if draft is None:
        raise HTTPException(404, "Draft not found")
    biz = await db.get(Business, draft.business_id)
    assert biz is not None
    return draft, biz


async def _out(db: DbSession, draft: EmailDraft, biz: Business) -> DraftOut:
    site = await db.get(GeneratedSite, draft.generated_site_id) if draft.generated_site_id else None
    return draft_out(draft, biz, site)


@router.get("", response_model=list[DraftOut])
async def list_drafts(
    _: CurrentUser,
    db: DbSession,
    status: DraftStatus | None = DraftStatus.DRAFTED,
    channel: OutreachChannel | None = None,
    business_id: uuid.UUID | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> list[DraftOut]:
    stmt = (
        select(EmailDraft, Business)
        .join(Business, Business.id == EmailDraft.business_id)
        .order_by(EmailDraft.created_at.desc(), EmailDraft.variant)
        .limit(limit)
    )
    if status:
        stmt = stmt.where(EmailDraft.status == status)
    if channel:
        stmt = stmt.where(EmailDraft.channel == channel)
    if business_id:
        stmt = stmt.where(EmailDraft.business_id == business_id)
    rows = (await db.execute(stmt)).all()
    site_ids = {d.generated_site_id for d, _ in rows if d.generated_site_id}
    sites = (
        {
            s.id: s
            for s in await db.scalars(select(GeneratedSite).where(GeneratedSite.id.in_(site_ids)))
        }
        if site_ids
        else {}
    )
    return [
        draft_out(d, b, sites.get(d.generated_site_id) if d.generated_site_id else None)
        for d, b in rows
    ]


@router.patch("/{draft_id}", response_model=DraftOut)
async def edit_draft(
    draft_id: uuid.UUID, body: DraftEdit, _: CurrentUser, db: DbSession
) -> DraftOut:
    draft, biz = await _load(db, draft_id)
    if draft.status != DraftStatus.DRAFTED:
        raise HTTPException(409, f"Only drafts can be edited (this one is {draft.status.value})")
    if body.subject is not None:
        draft.subject = body.subject
    if body.body is not None:
        text = body.body
        if draft.channel == OutreachChannel.EMAIL:
            # The opt-out link and postal address must survive any edit.
            unsub = ox.unsubscribe_url(get_settings(), draft.unsubscribe_token)
            text = ox.with_footer(text, load_agency(), unsub)
        draft.body = text
    await db.commit()
    return await _out(db, draft, biz)


@router.post("/{draft_id}/approve", response_model=DraftOut)
async def approve(
    draft_id: uuid.UUID,
    body: ApproveIn,
    user: CurrentUser,
    db: DbSession,
    dispatcher: OptionalDispatcher,
) -> DraftOut:
    draft, biz = await _load(db, draft_id)
    if draft.status != DraftStatus.DRAFTED:
        raise HTTPException(409, f"Draft is already {draft.status.value}")
    main_text = draft.body.split(ox.FOOTER_MARK, 1)[0]  # the footer is rebuilt at send time
    if "TODO" in main_text or "TODO" in (draft.subject or ""):
        raise HTTPException(
            409,
            "This draft still contains a TODO placeholder (fill in config/agency.yaml "
            "or edit the message) before approving",
        )
    if draft.channel == OutreachChannel.EMAIL:
        if not biz.primary_email:
            raise HTTPException(409, "No published email address for this business")
        if await ox.is_suppressed(db, biz, biz.primary_email):
            raise HTTPException(409, "This business is on the suppression list")
        if body.send_now and (missing := load_agency().unfilled()):
            raise HTTPException(
                409,
                "Fill in config/agency.yaml before sending (still TODO: "
                + ", ".join(missing)
                + ")",
            )
    draft.status = DraftStatus.APPROVED
    draft.approved_by_id = user.id
    draft.approved_at = datetime.now(UTC)
    await db.commit()
    if body.send_now and draft.channel == OutreachChannel.EMAIL:
        job, created = await create_job(
            db, queue=JobQueue.EMAIL, kind="send_email", business_id=biz.id,
            idempotency_key=f"send:{draft.id}", payload={"draft_id": str(draft.id)},
        )  # fmt: skip
        # If the queue is down, the send_due cron picks approved drafts up later.
        if created and dispatcher is not None:
            await dispatcher.dispatch(job)
    return await _out(db, draft, biz)


@router.post("/{draft_id}/reject", response_model=DraftOut)
async def reject(draft_id: uuid.UUID, _: CurrentUser, db: DbSession) -> DraftOut:
    draft, biz = await _load(db, draft_id)
    if draft.status not in OPEN:
        raise HTTPException(409, f"Draft is already {draft.status.value}")
    draft.status = DraftStatus.CANCELLED
    await db.commit()
    return await _out(db, draft, biz)


@router.post("/{draft_id}/mark", response_model=DraftOut)
async def mark(draft_id: uuid.UUID, body: MarkIn, _: CurrentUser, db: DbSession) -> DraftOut:
    """Record what happened: replied / won / lost, or 'sent' for a manually sent WhatsApp
    message or a completed call. Replies and outcomes stop any pending follow-ups."""
    draft, biz = await _load(db, draft_id)
    if body.status == DraftStatus.SENT:
        if draft.channel == OutreachChannel.EMAIL or draft.status != DraftStatus.APPROVED:
            raise HTTPException(409, "Only approved WhatsApp/SMS/call drafts can be marked sent")
        draft.status = DraftStatus.SENT
        draft.sent_at = datetime.now(UTC)
        biz.lead_status = LeadStatus.CONTACTED
    elif body.status in OUTCOMES:
        if draft.status != DraftStatus.SENT and draft.status not in OUTCOMES:
            raise HTTPException(409, "Only sent messages can be marked replied/won/lost")
        draft.status = body.status
        if lead := OUTCOMES[body.status]:
            biz.lead_status = lead
        await ox.cancel_pending(db, biz.id, body.status.value)
    else:
        raise HTTPException(422, "status must be sent, replied, won or lost")
    await db.commit()
    return await _out(db, draft, biz)
