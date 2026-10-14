"""Audit: score a website (a prospect's, or one we generated) on the versioned rubric."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urljoin

from pydantic import BaseModel, Field
from sqlalchemy import select

from leadforge.clients.browser import BrowserReport
from leadforge.clients.llm import Prompt
from leadforge.clients.psi import PsiResult
from leadforge.models import Audit, Business, Screenshot, Website
from leadforge.models.enums import (
    ApiProvider,
    AuditStatus,
    Grade,
    JobQueue,
    LeadStatus,
    Viewport,
    WebsiteStatus,
)
from leadforge.pipeline.context import JobContext
from leadforge.pipeline.registry import PermanentError, handler
from leadforge.scoring import rubric
from leadforge.scoring.signals import PageSignals, analyze, current_year
from leadforge.services.llm import call_structured
from leadforge.services.storage import get_storage
from leadforge.services.targets import load_targets
from leadforge.services.usage import record_usage

DESIGN_PROMPT = Prompt(
    id="design_review",
    version="1",
    system=(
        "You are a senior web designer reviewing a small local business website from two "
        "screenshots (desktop 1440px, mobile 390px). Score each criterion 0-5 against a fixed "
        "rubric: 5 = on par with a top modern agency site, 3 = acceptable but plain or dated, "
        "1 = clearly broken or amateur, 0 = nothing usable. Judge only what is visible. Be "
        "consistent: the same screenshots must always get the same scores."
    ),
    user=(
        "Business: {name} ({category}, {city}).\n"
        "Criteria: modernity, typography, spacing, colour, hierarchy, imagery, consistency.\n"
        "Return integer scores and a two-sentence rationale a business owner would understand."
    ),
)


class DesignReview(BaseModel):
    modernity: int = Field(ge=0, le=5)
    typography: int = Field(ge=0, le=5)
    spacing: int = Field(ge=0, le=5)
    colour: int = Field(ge=0, le=5)
    hierarchy: int = Field(ge=0, le=5)
    imagery: int = Field(ge=0, le=5)
    consistency: int = Field(ge=0, le=5)
    rationale: str


def heuristic_design(s: PageSignals) -> DesignReview:
    """Deterministic stand-in for the vision review (mock mode, or no screenshots)."""
    base = 4
    if not s.viewport:
        base -= 1
    if s.table_layout or s.font_tags:
        base -= 2
    if s.builder:
        base -= 1
    if s.outdated_markers:
        base -= 1
    rich = s.has_local_business_schema and s.og_image and s.cta_early
    base = max(0, min(5, base + (1 if rich else 0)))
    img = max(0, min(5, base + (1 if s.images and s.images_sized == s.images else -1)))
    return DesignReview(
        modernity=base,
        typography=max(0, base - (1 if s.tiny_inline_fonts else 0)),
        spacing=base,
        colour=max(0, base - (1 if s.font_tags else 0)),
        hierarchy=max(0, min(5, base + (0 if s.h1_count == 1 else -1))),
        imagery=img,
        consistency=base,
        rationale=(
            "Estimated from page structure (no visual review in mock mode): "
            + ("modern, responsive layout." if base >= 4 else "layout and styling look dated.")
        ),
    )


async def _robots_and_sitemap(ctx: JobContext, url: str, preview: bool) -> tuple[bool, bool]:
    fetcher = ctx.services.fetcher
    # Previews live under a sub-path, so their robots/sitemap are relative to it.
    root = url if preview else urljoin(url, "/")
    robots = await fetcher.get(urljoin(root, "robots.txt"), check_robots=False)
    robots_ok = robots.ok and "disallow: /\n" not in robots.text.lower() + "\n"
    has_sitemap = "sitemap:" in robots.text.lower() if robots.ok else False
    if not has_sitemap:
        sm = await fetcher.get(urljoin(root, "sitemap.xml"), check_robots=False)
        has_sitemap = sm.ok and "<urlset" in sm.text.lower()
    return robots_ok, has_sitemap


async def _broken_links(ctx: JobContext, links: list[str], limit: int = 10) -> tuple[int, int]:
    broken = checked = 0
    for link in links[:limit]:
        res = await ctx.services.fetcher.get(link)
        if res.error == "blocked_by_robots":
            continue
        checked += 1
        if res.error or res.status >= 400:
            broken += 1
    return broken, checked


def _psi_evidence(r: PsiResult | None) -> dict[str, Any] | None:
    if r is None:
        return None
    return {
        "performance": r.performance, "accessibility": r.accessibility, "lcp_ms": r.lcp_ms,
        "cls": r.cls, "tbt_ms": r.tbt_ms, "inp_ms": r.inp_ms, "total_bytes": r.total_bytes,
        "mocked": r.mocked,
    }  # fmt: skip


async def run_audit(
    ctx: JobContext,
    biz: Business,
    url: str,
    *,
    website: Website | None = None,
    generated_site_id: uuid.UUID | None = None,
) -> Audit:
    """Fetch, measure and score `url`, persisting an Audit (+ screenshots)."""
    services = ctx.services
    settings = services.settings
    audit = Audit(
        business_id=biz.id,
        website_id=website.id if website else None,
        generated_site_id=generated_site_id,
        target_url=url,
        rubric_version=rubric.RUBRIC_VERSION,
        status=AuditStatus.RUNNING,
    )
    ctx.db.add(audit)
    await ctx.db.flush()

    home = await services.fetcher.get(url, check_robots=generated_site_id is None)
    if home.is_challenge:
        audit.status = AuditStatus.FAILED
        audit.error = "bot challenge (e.g. Cloudflare) blocked the audit; needs a manual look"
        return audit
    if home.error or not home.ok or home.is_parked:
        reason = "parked" if home.is_parked else home.error or f"HTTP {home.status}"
        audit.status = AuditStatus.COMPLETED
        audit.total_score = 0
        audit.grade = Grade.D
        audit.breakdown = {c: {"score": 0.0, "max": m} for c, m in rubric.CATEGORY_MAX.items()}
        audit.top_issues = [
            "Your domain shows a 'for sale' parking page instead of your business"
            if home.is_parked
            else "Your website didn't load when we tried it, so customers likely can't reach it either"
        ]
        audit.evidence = {"fetch": {"status": home.status, "error": reason}}
        audit.cached_until = datetime.now(UTC) + timedelta(days=7)
        return audit

    preview = generated_site_id is not None
    robots_ok, has_sitemap = await _robots_and_sitemap(ctx, home.final_url, preview)
    signals = analyze(home.text, home.final_url, biz.name, biz.phone_e164 or "")
    broken, checked = await _broken_links(
        ctx, [u for u in signals.internal_links if u != home.final_url]
    )

    psi_m = await services.psi.run(home.final_url, "mobile", home.text)
    psi_d = await services.psi.run(home.final_url, "desktop", home.text)
    for r in (psi_m, psi_d):
        await record_usage(
            ctx.db, ApiProvider.PAGESPEED, f"run_{r.strategy}", mocked=r.mocked, job_id=ctx.job.id
        )

    browser: BrowserReport | None = None
    if settings.browser_audits:
        browser = await services.browser.probe(home.final_url)
    storage = get_storage()
    shots: dict[str, bytes] = browser.screenshots if browser and browser.available else {}
    for name, png in shots.items():
        key = f"screenshots/{audit.id}/{name}.png"
        storage.put(key, png)
        ctx.db.add(
            Screenshot(
                audit_id=audit.id,
                viewport=Viewport(name),
                storage_key=key,
                width=1440 if name == "desktop_1440" else 390,
                height=900 if name == "desktop_1440" else 844,
            )
        )

    targets = load_targets()
    cat = next((c for c in targets.categories if c.id == biz.category), None)
    review = (
        (
            await call_structured(
                ctx.db,
                services.llm,
                DESIGN_PROMPT,
                {
                    "name": biz.name,
                    "category": cat.label if cat else biz.category,
                    "city": biz.city,
                },
                DesignReview,
                mock=lambda: heuristic_design(signals),
                images=[shots[k] for k in ("desktop_1440", "mobile_390") if k in shots] or None,
                job_id=ctx.job.id,
            )
        ).data
        if shots or services.mock
        else heuristic_design(signals)
    )

    inputs = rubric.AuditInputs(
        url=url, final_url=home.final_url, status=home.status, headers=home.headers,
        signals=signals, psi_mobile=psi_m, psi_desktop=psi_d, browser=browser,
        design_scores=review.model_dump(exclude={"rationale"}),
        design_rationale=review.rationale, has_sitemap=has_sitemap, robots_txt_ok=robots_ok,
        broken_links=broken, links_checked=checked, business_name=biz.name,
        phone_digits="".join(ch for ch in (biz.phone_e164 or "") if ch.isdigit()),
        page_text=home.text, year=current_year(), preview=preview,
    )  # fmt: skip
    result = rubric.score(inputs)
    audit.status = AuditStatus.COMPLETED
    audit.total_score = result.total
    audit.grade = Grade(result.grade)
    audit.breakdown = result.breakdown
    audit.top_issues = result.top_issues
    audit.evidence = {
        "checks": [
            {"id": c.id, "category": c.category, "earned": round(c.earned, 2),
             "max": c.max_points, "issue": c.issue, "evidence": c.evidence}
            for c in result.checks
        ],
        "psi": {"mobile": _psi_evidence(psi_m), "desktop": _psi_evidence(psi_d)},
        "browser": {
            "available": bool(browser and browser.available),
            "error": browser.error if browser else "disabled",
        },
        "design_review": review.model_dump(),
        "fetch": {"status": home.status, "final_url": home.final_url, "bytes": home.bytes,
                  "elapsed_ms": home.elapsed_ms},
    }  # fmt: skip
    audit.cached_until = datetime.now(UTC) + timedelta(days=targets.defaults.audit_cache_days)
    return audit


def apply_to_business(biz: Business, total: int, grade: str, threshold: int) -> bool:
    """Update the lead from an audit result. Returns True if it should be rebuilt."""
    biz.latest_score = total
    biz.latest_grade = grade
    biz.audited_at = datetime.now(UTC)
    rebuild = total < threshold
    biz.lead_status = LeadStatus.REBUILD_QUEUED if rebuild else LeadStatus.AUDITED
    return rebuild


@handler("audit")
async def audit_handler(ctx: JobContext) -> dict[str, Any]:
    biz = await ctx.db.get(Business, ctx.job.business_id)
    if biz is None:
        raise PermanentError("business not found")
    targets = load_targets()
    threshold = targets.defaults.rebuild_threshold
    cat = next((c for c in targets.categories if c.id == biz.category), None)

    site = await ctx.db.scalar(select(Website).where(Website.business_id == biz.id))
    if site is None:
        # No website: score 0, hottest lead, straight to the rebuild queue.
        result = rubric.no_website_result(cat.label if cat else biz.category, biz.city)
        apply_to_business(biz, 0, "D", threshold)
        await ctx.db.commit()
        await _queue_generate(ctx, biz)
        return {"score": 0, "grade": "D", "has_website": False, "issues": result.top_issues}

    cached = await ctx.db.scalar(
        select(Audit)
        .where(
            Audit.website_id == site.id,
            Audit.status == AuditStatus.COMPLETED,
            Audit.rubric_version == rubric.RUBRIC_VERSION,
            Audit.cached_until > datetime.now(UTC),
        )
        .order_by(Audit.created_at.desc())
        .limit(1)
    )
    audit = cached if cached and not ctx.job.payload.get("force") else None
    if audit is None:
        audit = await run_audit(ctx, biz, site.final_url or site.url, website=site)
    if audit.status == AuditStatus.FAILED:
        biz.lead_status = LeadStatus.AUDITED
        await ctx.db.commit()
        return {"status": "failed", "error": audit.error}

    assert audit.total_score is not None and audit.grade is not None
    rebuild = apply_to_business(biz, audit.total_score, audit.grade.value, threshold)
    if site.status == WebsiteStatus.PENDING:
        site.status = WebsiteStatus.OK
    await ctx.db.commit()
    if rebuild:
        await _queue_generate(ctx, biz)
    return {
        "audit_id": str(audit.id), "score": audit.total_score, "grade": audit.grade.value,
        "cached": audit is cached, "rebuild": rebuild, "top_issues": audit.top_issues,
    }  # fmt: skip


async def _queue_generate(ctx: JobContext, biz: Business) -> None:
    await ctx.enqueue(
        JobQueue.GENERATE,
        "generate",
        f"generate:{biz.id}",
        {"business_id": str(biz.id)},
        business_id=biz.id,
    )
