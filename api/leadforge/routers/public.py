"""Unauthenticated endpoints: generated-site contact forms, one-click unsubscribe,
locally hosted previews and stored files (screenshots)."""

import hashlib
import html
import mimetypes
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, EmailStr, Field, ValidationError, model_validator
from sqlalchemy import select

from leadforge.core.config import Settings, get_settings
from leadforge.core.deps import DbSession
from leadforge.core.ratelimit import limiter
from leadforge.models import Business, EmailDraft, EmailEvent, FormSubmission, GeneratedSite
from leadforge.models.enums import EmailEventType, GeneratedSiteStatus, LeadStatus
from leadforge.services import outreach as ox
from leadforge.services.previews import preview_response
from leadforge.services.storage import get_storage
from leadforge.services.suppression import suppress

router = APIRouter(tags=["public"])


class ContactForm(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=40, pattern=r"^[+\d][\d\s().-]{5,}$")
    message: str = Field(min_length=1, max_length=4000)
    company_website: str | None = Field(None, max_length=200)  # honeypot: humans leave it empty
    turnstile_token: str | None = Field(None, alias="cf-turnstile-response", max_length=4096)

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _reachable(self) -> "ContactForm":
        if not self.email and not self.phone:
            raise ValueError("Add an email address or phone number so we can reply")
        return self


async def verify_turnstile(settings: Settings, token: str | None, ip: str | None) -> bool:
    if settings.mock_apis or settings.turnstile_secret_key is None:
        return True
    if not token:
        return False
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": settings.turnstile_secret_key.get_secret_value(),
                "response": token,
                "remoteip": ip or "",
            },
        )
    return bool(resp.status_code == 200 and resp.json().get("success"))


PUBLIC_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


@router.options("/api/public/forms/{site_id}", include_in_schema=False)
async def form_preflight(site_id: uuid.UUID) -> Response:
    return Response(status_code=204, headers=PUBLIC_CORS)


@router.post("/api/public/forms/{site_id}", status_code=202)
@limiter.limit("5/minute")
async def submit_form(request: Request, site_id: uuid.UUID, db: DbSession) -> Response:
    """Accepts JSON (fetch from the Next.js template) or a plain HTML form post."""
    is_json = request.headers.get("content-type", "").startswith("application/json")
    raw = await request.json() if is_json else dict(await request.form())
    if not isinstance(raw, dict):
        raise HTTPException(422, "Expected an object")
    try:
        form = ContactForm.model_validate({k: v or None for k, v in raw.items()})
    except ValidationError as exc:
        msg = "; ".join(str(e["msg"]).removeprefix("Value error, ") for e in exc.errors())
        if is_json:
            return JSONResponse({"detail": msg}, status_code=422, headers=PUBLIC_CORS)
        return _page(
            "Please check the form",
            f"<h1>Please check the form</h1><p>{html.escape(msg)}</p>"
            "<p><a href='javascript:history.back()'>Go back</a></p>",
            422,
        )

    site = await db.get(GeneratedSite, site_id)
    if site is None or site.status == GeneratedSiteStatus.EXPIRED:
        raise HTTPException(404, "Form not found")
    if not form.company_website:  # honeypot filled = bot: pretend success, store nothing
        ip = request.client.host if request.client else None
        if not await verify_turnstile(get_settings(), form.turnstile_token, ip):
            raise HTTPException(400, "Verification failed, please try again")
        db.add(
            FormSubmission(
                generated_site_id=site.id,
                name=form.name,
                email=str(form.email) if form.email else None,
                phone=form.phone,
                message=form.message,
                ip_hash=hashlib.sha256(ip.encode()).hexdigest() if ip else None,
            )
        )
        await db.commit()
    if is_json:
        return JSONResponse({"status": "ok"}, status_code=202, headers=PUBLIC_CORS)
    return _page(
        "Message sent",
        "<h1>Thanks, your message was sent.</h1>"
        "<p><a href='javascript:history.back()'>Back to the site</a></p>",
        202,
    )


def _page(title: str, body: str, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(
        status_code=status_code,
        content="<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='robots' content='noindex'>"
        f"<title>{html.escape(title)}</title><style>body{{font:16px/1.5 system-ui,sans-serif;"
        "max-width:32rem;margin:4rem auto;padding:0 1rem;color:#111}button{font:inherit;"
        "padding:.75rem 1.25rem;border-radius:.5rem;border:0;background:#111;color:#fff;"
        f"min-height:48px;cursor:pointer}}</style></head><body>{body}</body></html>",
    )


async def _draft_by_token(db: DbSession, token: str) -> EmailDraft:
    draft = await db.scalar(select(EmailDraft).where(EmailDraft.unsubscribe_token == token))
    if draft is None:
        raise HTTPException(404, "Unknown link")
    return draft


@router.get("/u/{token}", response_class=HTMLResponse)
async def unsubscribe_page(token: str, db: DbSession) -> HTMLResponse:
    """Confirmation page. GET never unsubscribes, so link scanners can't trigger it."""
    await _draft_by_token(db, token)
    return _page(
        "Unsubscribe",
        "<h1>Stop these emails?</h1><p>We'll never email this address again.</p>"
        f"<form method='post' action='/u/{html.escape(token)}'>"
        "<button type='submit'>Unsubscribe</button></form>",
    )


@router.post("/u/{token}", response_class=HTMLResponse)
async def unsubscribe(token: str, db: DbSession) -> HTMLResponse:
    """One-click unsubscribe (RFC 8058) and the confirmation form both land here."""
    draft = await _draft_by_token(db, token)
    biz = await db.get(Business, draft.business_id)
    assert biz is not None
    if biz.primary_email:
        await suppress(
            db, email=biz.primary_email, reason="unsubscribe", source=f"draft:{draft.id}"
        )
    elif biz.domain:
        await suppress(db, domain=biz.domain, reason="unsubscribe", source=f"draft:{draft.id}")
    await ox.cancel_pending(db, biz.id, "unsubscribed")
    biz.lead_status = LeadStatus.SUPPRESSED
    db.add(
        EmailEvent(
            draft_id=draft.id, type=EmailEventType.UNSUBSCRIBED, occurred_at=datetime.now(UTC)
        )
    )
    await db.commit()
    return _page("Unsubscribed", "<h1>You're unsubscribed.</h1><p>Sorry for the bother.</p>")


@router.get("/previews/{slug}/{path:path}", include_in_schema=False)
async def preview(slug: str, path: str) -> Response:
    settings = get_settings()
    url = f"{settings.public_base_url.rstrip('/')}/previews/{slug}/{path}"
    result = preview_response(settings, url)
    if result is None:
        raise HTTPException(404)
    code, headers, body = result
    return Response(body, status_code=code, headers=headers)


@router.get("/files/{key:path}", include_in_schema=False)
async def files(key: str) -> FileResponse:
    try:
        path = get_storage().path(key)
    except ValueError:
        raise HTTPException(404) from None
    if not key.startswith("screenshots/") or not path.is_file():
        raise HTTPException(404)
    return FileResponse(
        path,
        media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=86400", "X-Robots-Tag": "noindex"},
    )
