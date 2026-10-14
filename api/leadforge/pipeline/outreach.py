"""Outreach: draft messages (never send unapproved), send approved ones, follow-ups."""

import functools
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update

from leadforge.clients.email import OutgoingEmail
from leadforge.models import Audit, Business, EmailDraft, EmailEvent, GeneratedSite, Screenshot
from leadforge.models.enums import (
    AuditStatus,
    DraftStatus,
    EmailEventType,
    GeneratedSiteStatus,
    LeadStatus,
    OutreachChannel,
)
from leadforge.pipeline.context import JobContext
from leadforge.pipeline.registry import PermanentError, handler
from leadforge.prompts.outreach import CALL_SCRIPT, OUTREACH_EMAIL, WHATSAPP_MESSAGE
from leadforge.services import outreach as ox
from leadforge.services.agency import load_agency
from leadforge.services.llm import call_structured
from leadforge.services.storage import get_storage

FOLLOW_UP_DAYS = (3, 7)


async def _screens(ctx: JobContext, audit_id: uuid.UUID | None) -> dict[str, str]:
    if audit_id is None:
        return {}
    rows = await ctx.db.scalars(select(Screenshot).where(Screenshot.audit_id == audit_id))
    storage = get_storage()
    return {r.viewport.value: storage.url(r.storage_key) for r in rows}


@handler("draft_outreach")
async def draft_outreach(ctx: JobContext) -> dict[str, Any]:
    biz = await ctx.db.get(Business, ctx.job.business_id)
    site = await ctx.db.get(GeneratedSite, uuid.UUID(ctx.job.payload["generated_site_id"]))
    if biz is None or site is None:
        raise PermanentError("business or generated site not found")
    if site.status != GeneratedSiteStatus.LIVE:
        raise PermanentError("generated site is not live")
    if await ox.is_suppressed(ctx.db, biz, biz.primary_email):
        biz.lead_status = LeadStatus.SUPPRESSED
        await ctx.db.commit()
        return {"status": "suppressed"}

    agency = load_agency()
    settings = ctx.services.settings
    before = await ctx.db.scalar(
        select(Audit).where(Audit.business_id == biz.id, Audit.website_id.is_not(None),
                            Audit.status == AuditStatus.COMPLETED)
        .order_by(Audit.created_at.desc()).limit(1)
    )  # fmt: skip
    after = await ctx.db.scalar(
        select(Audit).where(Audit.generated_site_id == site.id, Audit.status == AuditStatus.COMPLETED)
        .order_by(Audit.created_at.desc()).limit(1)
    )  # fmt: skip
    shots_before = await _screens(ctx, before.id if before else None)
    shots_after = await _screens(ctx, after.id if after else None)
    issues = (before.top_issues if before else None) or [
        "You don't have a website yet, so people searching online can't find you"
    ]
    facts: dict[str, Any] = {
        "business_name": biz.name,
        "city": biz.city,
        "issues": issues[:3],
        "score_before": site.baseline_score or 0,
        "score_after": site.score,
        "preview_url": site.preview_url,
        "price_from": ox.price_hint(agency, biz.country),
        "booking_url": None if agency.booking_url.startswith("TODO") else agency.booking_url,
        "screenshots": {"before": shots_before, "after": shots_after},
    }
    created: list[str] = []
    existing = await ctx.db.scalar(
        select(EmailDraft.id).where(EmailDraft.business_id == biz.id,
                                    EmailDraft.generated_site_id == site.id).limit(1)
    )  # fmt: skip
    if existing:
        return {"status": "exists"}

    if biz.primary_email:
        result = await call_structured(
            ctx.db, ctx.services.llm, OUTREACH_EMAIL,
            {"facts": json.dumps(facts, ensure_ascii=False), "sender_name": agency.sender_name,
             "agency_name": agency.agency_name},
            ox.EmailCopy, mock=lambda: ox.mock_email(facts, agency), job_id=ctx.job.id,
        )  # fmt: skip
        copy = result.data
        body = copy.body.strip()
        if ox.word_count(body) > ox.MAX_BODY_WORDS:
            words = body.split()
            body = " ".join(words[: ox.MAX_BODY_WORDS])
        shots = ""
        if shots_before.get("mobile_390") and shots_after.get("mobile_390"):
            shots = f"\n\nBefore / after on a phone: {shots_before['mobile_390']} | {shots_after['mobile_390']}"
        for variant, subject in (("A", copy.subject_a), ("B", copy.subject_b)):
            token = ox.new_token()
            draft = EmailDraft(
                business_id=biz.id, generated_site_id=site.id, channel=OutreachChannel.EMAIL,
                variant=variant, subject=subject,
                body=body + shots + ox.compliance_footer(agency, ox.unsubscribe_url(settings, token)),
                unsubscribe_token=token, prompt_version=result.prompt_ref,
            )  # fmt: skip
            ctx.db.add(draft)
            created.append(f"email:{variant}")
    else:
        for channel, prompt, mock_text in (
            (OutreachChannel.WHATSAPP, WHATSAPP_MESSAGE,
             f"Hello {biz.name}, I'm {agency.sender_name} from {agency.agency_name}. I made a free "
             f"preview of a new website for you: {site.preview_url}. Would you like to hear more? "
             "Reply STOP and I won't message again."),
            (OutreachChannel.CALL_SCRIPT, CALL_SCRIPT,
             f"Opening: Hi, is this {biz.name}? I'm {agency.sender_name} from {agency.agency_name}. "
             "Do you have one minute?\n"
             + "\n".join(f"Point: {i}" for i in issues[:3])
             + f"\nOffer: I built a free preview ({site.preview_url}). Can I send it on WhatsApp?\n"
             "If not interested: Thank you, I'll make sure we don't call again.\n"
             "Close: Thanks for your time."),
        ):  # fmt: skip
            result_msg = await call_structured(
                ctx.db, ctx.services.llm, prompt, {"facts": json.dumps(facts, ensure_ascii=False)},
                ox.ShortMessage, mock=functools.partial(ox.ShortMessage, text=mock_text), job_id=ctx.job.id,
            )  # fmt: skip
            ctx.db.add(EmailDraft(
                business_id=biz.id, generated_site_id=site.id, channel=channel, variant="A",
                subject=None, body=result_msg.data.text, unsubscribe_token=ox.new_token(),
                prompt_version=result_msg.prompt_ref,
            ))  # fmt: skip
            created.append(channel.value)
    await ctx.db.commit()
    return {"status": "drafted", "drafts": created}


async def send_one(ctx: JobContext, draft: EmailDraft) -> str:
    """Send a single approved email draft. Every guard runs again at send time."""
    settings = ctx.services.settings
    agency = load_agency()
    if draft.status != DraftStatus.APPROVED or draft.approved_by_id is None:
        return "not_approved"
    if draft.channel != OutreachChannel.EMAIL:
        return "not_email"
    if missing := agency.unfilled():
        raise PermanentError(
            f"agency details still TODO: {', '.join(missing)} (config/agency.yaml)"
        )
    biz = await ctx.db.get(Business, draft.business_id)
    assert biz is not None
    to = biz.primary_email
    if not to:
        return "no_email"
    if await ox.is_suppressed(ctx.db, biz, to):
        await ox.cancel_pending(ctx.db, biz.id, "suppressed")
        await ctx.db.commit()
        return "suppressed"
    if await ox.sent_today(ctx.db) >= settings.email_daily_limit:
        return "throttled"
    # Claim the draft atomically so a cron run and a send job can never both send it.
    claim = f"claim:{ctx.job.id}"
    claimed = await ctx.db.execute(
        update(EmailDraft)
        .where(EmailDraft.id == draft.id, EmailDraft.status == DraftStatus.APPROVED,
               EmailDraft.provider_message_id.is_(None))
        .values(provider_message_id=claim)
    )  # fmt: skip
    await ctx.db.commit()
    if claimed.rowcount != 1:  # type: ignore[attr-defined]
        return "already_claimed"
    await ctx.db.refresh(draft)
    unsub = ox.unsubscribe_url(settings, draft.unsubscribe_token)
    try:
        message_id = await _deliver(ctx, draft, to, unsub, agency)
    except Exception:
        draft.provider_message_id = None
        await ctx.db.commit()
        raise
    await _record_sent(ctx, draft, biz, message_id)
    return "sent"


async def _deliver(ctx: JobContext, draft: EmailDraft, to: str, unsub: str, agency: Any) -> str:
    text = ox.with_footer(draft.body, agency, unsub)
    return await ctx.services.sender.send(
        OutgoingEmail(
            to=to,
            from_=f"{agency.sender_name} <{agency.sender_email}>",
            subject=draft.subject or "",
            text=text,
            html='<pre style="font:inherit;white-space:pre-wrap">'
            + text.replace("&", "&amp;").replace("<", "&lt;")
            + "</pre>",
            headers={
                "List-Unsubscribe": f"<{unsub}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
            reply_to=agency.sender_email,
        )
    )


async def _record_sent(ctx: JobContext, draft: EmailDraft, biz: Business, message_id: str) -> None:
    now = datetime.now(UTC)
    draft.status = DraftStatus.SENT
    draft.sent_at = now
    draft.provider_message_id = message_id
    ctx.db.add(
        EmailEvent(
            draft_id=draft.id,
            type=EmailEventType.SENT,
            occurred_at=now,
            payload={"provider": ctx.services.sender.name},
        )
    )
    biz.lead_status = LeadStatus.CONTACTED
    # Cancel the other A/B variant of this initial email.
    if draft.sequence_day == 0:
        others = await ctx.db.scalars(
            select(EmailDraft).where(
                EmailDraft.business_id == biz.id, EmailDraft.id != draft.id,
                EmailDraft.sequence_day == 0, EmailDraft.channel == OutreachChannel.EMAIL,
                EmailDraft.status.in_([DraftStatus.DRAFTED, DraftStatus.APPROVED]),
            )
        )  # fmt: skip
        for o in others:
            o.status = DraftStatus.CANCELLED
        await _create_follow_ups(ctx, draft, now)
    await ctx.db.commit()


async def _create_follow_ups(ctx: JobContext, parent: EmailDraft, sent_at: datetime) -> None:
    """Day 3 and day 7 follow-ups, as drafts that still need a human to approve them."""
    agency = load_agency()
    settings = ctx.services.settings
    site = (
        await ctx.db.get(GeneratedSite, parent.generated_site_id)
        if parent.generated_site_id
        else None
    )
    preview = site.preview_url if site else ""
    for day in FOLLOW_UP_DAYS:
        token = ox.new_token()
        body = (
            f"Hi again, just checking you saw the free preview I made: {preview}\n\n"
            "If now isn't the right time, no problem. Reply and I'll answer any questions."
            if day == 3
            else "Last note from me: the free preview stays up for a few more weeks if you'd "
            f"like to take a look ({preview}). I won't follow up again."
        )
        ctx.db.add(EmailDraft(
            business_id=parent.business_id, generated_site_id=parent.generated_site_id,
            contact_id=parent.contact_id, channel=OutreachChannel.EMAIL, variant=parent.variant,
            subject=f"Re: {parent.subject}", sequence_day=day, parent_draft_id=parent.id,
            body=body + ox.compliance_footer(agency, ox.unsubscribe_url(settings, token)),
            unsubscribe_token=token, scheduled_for=sent_at + timedelta(days=day),
            prompt_version="follow_up@1",
        ))  # fmt: skip


@handler("send_email")
async def send_email(ctx: JobContext) -> dict[str, Any]:
    draft = await ctx.db.get(EmailDraft, uuid.UUID(ctx.job.payload["draft_id"]))
    if draft is None:
        raise PermanentError("draft not found")
    if draft.scheduled_for and draft.scheduled_for.replace(
        tzinfo=draft.scheduled_for.tzinfo or UTC
    ) > datetime.now(UTC):
        return {"status": "not_due"}
    return {"status": await send_one(ctx, draft)}


@handler("send_due")
async def send_due(ctx: JobContext) -> dict[str, Any]:
    """Cron: send approved drafts that are due, within the daily limit. Follow-ups stop
    automatically once the lead replied, unsubscribed, or was marked won/lost."""
    now = datetime.now(UTC)
    drafts = list(
        await ctx.db.scalars(
            select(EmailDraft)
            .where(
                EmailDraft.status == DraftStatus.APPROVED,
                EmailDraft.channel == OutreachChannel.EMAIL,
            )
            .order_by(EmailDraft.approved_at)
        )
    )
    results: dict[str, int] = {}
    for d in drafts:
        if d.scheduled_for and d.scheduled_for.replace(tzinfo=d.scheduled_for.tzinfo or UTC) > now:
            continue
        if d.parent_draft_id:
            parent = await ctx.db.get(EmailDraft, d.parent_draft_id)
            if parent and parent.status in (
                DraftStatus.REPLIED,
                DraftStatus.WON,
                DraftStatus.LOST,
                DraftStatus.CANCELLED,
            ):
                d.status = DraftStatus.CANCELLED
                await ctx.db.commit()
                results["cancelled"] = results.get("cancelled", 0) + 1
                continue
        status = await send_one(ctx, d)
        results[status] = results.get(status, 0) + 1
        if status == "throttled":
            break
    return results
