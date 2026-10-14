"""Delivery events from the email provider (Resend signs webhooks with Svix)."""

import base64
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from leadforge.core.config import get_settings
from leadforge.core.deps import DbSession
from leadforge.models import Business, EmailDraft, EmailEvent
from leadforge.models.enums import EmailEventType, LeadStatus
from leadforge.services import outreach as ox
from leadforge.services.suppression import suppress

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

EVENT_TYPES = {
    "email.delivered": EmailEventType.DELIVERED,
    "email.opened": EmailEventType.OPENED,
    "email.clicked": EmailEventType.CLICKED,
    "email.bounced": EmailEventType.BOUNCED,
    "email.complained": EmailEventType.COMPLAINED,
}
TOLERANCE_S = 300


def verify_svix(
    secret: str, headers: dict[str, str], body: bytes, now: float | None = None
) -> bool:
    msg_id, ts, sigs = (headers.get(h) for h in ("svix-id", "svix-timestamp", "svix-signature"))
    if not (msg_id and ts and sigs):
        return False
    try:
        if abs((now or time.time()) - int(ts)) > TOLERANCE_S:
            return False
        key = base64.b64decode(secret.removeprefix("whsec_"))
    except ValueError:
        return False
    signed = f"{msg_id}.{ts}.".encode() + body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    return any(
        hmac.compare_digest(expected, part.split(",", 1)[1])
        for part in sigs.split()
        if part.startswith("v1,")
    )


@router.post("/email")
async def email_webhook(request: Request, db: DbSession) -> dict[str, str]:
    settings = get_settings()
    body = await request.body()
    secret = settings.resend_webhook_secret
    if secret is None:
        if not settings.mock_apis:
            raise HTTPException(503, "RESEND_WEBHOOK_SECRET is not configured")
    elif not verify_svix(secret.get_secret_value(), dict(request.headers), body):
        raise HTTPException(401, "Bad signature")
    payload: dict[str, Any] = json.loads(body or b"{}")
    kind = EVENT_TYPES.get(str(payload.get("type")))
    message_id = (payload.get("data") or {}).get("email_id")
    if kind is None or not message_id:
        return {"status": "ignored"}
    draft = await db.scalar(select(EmailDraft).where(EmailDraft.provider_message_id == message_id))
    if draft is None:
        return {"status": "unknown_message"}
    db.add(EmailEvent(draft_id=draft.id, type=kind, payload=payload, occurred_at=datetime.now(UTC)))
    if kind in (EmailEventType.BOUNCED, EmailEventType.COMPLAINED):
        biz = await db.get(Business, draft.business_id)
        assert biz is not None
        if biz.primary_email:
            await suppress(
                db, email=biz.primary_email, reason=kind.value, source=f"webhook:{message_id}"
            )
        await ox.cancel_pending(db, biz.id, kind.value)
        biz.lead_status = LeadStatus.SUPPRESSED
    await db.commit()
    return {"status": "recorded"}
