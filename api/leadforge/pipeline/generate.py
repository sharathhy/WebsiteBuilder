"""Generate: build a replacement site from a JSON spec, deploy a noindex preview,
re-score it on the same rubric, and gate on quality (auto-fix up to 3 attempts)."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from leadforge.models import Audit, Business, Contact, GeneratedSite, Website
from leadforge.models.enums import (
    ApiProvider,
    AuditStatus,
    ContactKind,
    GeneratedSiteStatus,
    JobQueue,
    LeadStatus,
)
from leadforge.pipeline.audit import run_audit
from leadforge.pipeline.context import JobContext
from leadforge.pipeline.registry import PermanentError, handler
from leadforge.prompts.site_copy import SITE_COPY
from leadforge.schemas.site_spec import SPEC_VERSION, ImageAsset
from leadforge.services import pages as page_inventory
from leadforge.services import sitespec
from leadforge.services.art import hero_svg
from leadforge.services.brand import build_palette
from leadforge.services.llm import call_structured
from leadforge.services.sitebuild import BuildError, build_site
from leadforge.services.targets import load_targets
from leadforge.services.usage import record_usage

MAX_ATTEMPTS = 3
GATE_MIN_SCORE = 90
GATE_MIN_IMPROVEMENT = 30


def gate(score: int, baseline: int, missing: list[str] | None = None) -> tuple[bool, str | None]:
    if missing:
        shown = ", ".join(missing[:5]) + (
            f" and {len(missing) - 5} more" if len(missing) > 5 else ""
        )
        return False, f"missing {len(missing)} of the current site's pages: {shown}"
    if score < GATE_MIN_SCORE:
        return False, f"score {score} < {GATE_MIN_SCORE}"
    if score - baseline < GATE_MIN_IMPROVEMENT:
        return False, f"improvement {score - baseline} < {GATE_MIN_IMPROVEMENT}"
    return True, None


# Auto-fix plan per retry: progressively lighter builds.
FIX_PLAN: list[dict[str, Any]] = [
    {},
    {"enable_3d": False},
    {"enable_3d": False, "gallery": False},
]


@handler("generate")
async def generate(ctx: JobContext) -> dict[str, Any]:
    biz = await ctx.db.get(Business, ctx.job.business_id)
    if biz is None:
        raise PermanentError("business not found")
    settings = ctx.services.settings
    targets = load_targets()
    cat = next((c for c in targets.categories if c.id == biz.category), None)
    template = cat.template if cat else "generic-premium"
    label = cat.label if cat else biz.category.replace("-", " ").title()
    locale = "en-IN" if biz.country == "IN" else "en-US"

    contacts = list(await ctx.db.scalars(select(Contact).where(Contact.business_id == biz.id)))
    whatsapp = next((c.value for c in contacts if c.kind == ContactKind.WHATSAPP), None)
    socials = [c.value for c in contacts if c.kind == ContactKind.SOCIAL]
    latest = await ctx.db.scalar(
        select(Audit).where(Audit.business_id == biz.id, Audit.website_id.is_not(None),
                            Audit.status == AuditStatus.COMPLETED)
        .order_by(Audit.created_at.desc()).limit(1)
    )  # fmt: skip
    baseline = biz.latest_score or 0
    issues = latest.top_issues if latest else ["No website"]

    site_html = None
    website = await ctx.db.scalar(select(Website).where(Website.business_id == biz.id))
    if website is not None:
        home = await ctx.services.fetcher.get(website.final_url or website.url)
        site_html = home.text if home.ok and not home.is_parked else None
        if site_html is not None and not website.page_inventory:
            # Crawled before page parity existed: list the pages now.
            found, stats = await page_inventory.build_inventory(
                ctx.services.fetcher, home, max_pages=settings.page_inventory_max
            )
            website.page_inventory = [p.as_dict() for p in found]
            website.page_inventory_stats = stats
    palette = build_palette(template, site_html)
    # Page parity: every page of the current site gets a page on the new one.
    inventory = [p for p in (website.page_inventory if website else []) if p.get("fetched", True)]

    site = await ctx.db.scalar(
        select(GeneratedSite).where(GeneratedSite.business_id == biz.id)
        .order_by(GeneratedSite.created_at.desc()).limit(1)
    )  # fmt: skip
    if site is not None and site.status == GeneratedSiteStatus.LIVE:
        if not ctx.job.payload.get("force"):
            return {"status": "already_live", "preview_url": site.preview_url}
        site = None  # a reviewer asked for a fresh build; the old preview stays until expiry
    if site is None:
        site = GeneratedSite(
            business_id=biz.id,
            template=template,
            spec_version=SPEC_VERSION,
            baseline_score=baseline,
        )
        ctx.db.add(site)
        await ctx.db.flush()
    site.status = GeneratedSiteStatus.GENERATING
    site.baseline_score = baseline
    await ctx.db.commit()

    primary_keyword = f"{label.lower()} in {biz.city}"
    copy = (
        await call_structured(
            ctx.db,
            ctx.services.llm,
            SITE_COPY,
            {
                "locale": locale,
                "primary_keyword": primary_keyword,
                "facts": json.dumps(sitespec.facts_for(biz), ensure_ascii=False),
                "issues": "\n".join(f"- {i}" for i in issues),
            },
            sitespec.SiteCopy,
            mock=lambda: sitespec.mock_copy(biz, label, template, locale),
            job_id=ctx.job.id,
            estimate_usd=0.10,
        )
    ).data

    slug = sitespec.site_slug(biz)
    deployer = ctx.services.deployer
    base_url = deployer.base_url_for(slug)
    base_path = base_url.split("://", 1)[1].split("/", 1)[1] if base_url.count("/") > 2 else ""
    base_path = f"/{base_path}" if base_path else ""
    hero = ImageAsset(
        src=f"{base_path}/generated/hero.svg", alt=f"Abstract illustration in {biz.name}'s colours"
    )

    history: list[dict[str, Any]] = []
    passed = False
    for attempt, fix in enumerate(FIX_PLAN[:MAX_ATTEMPTS], start=1):
        site.attempts = attempt
        spec = sitespec.build_spec(
            biz=biz,
            copy=copy,
            template=template,
            palette=palette,
            site_url=base_url + "/",
            site_id=str(site.id),
            form_endpoint=f"{settings.public_base_url.rstrip('/')}/api/public/forms/{site.id}",
            whatsapp=whatsapp,
            email=biz.primary_email,
            socials=socials,
            hero_image=hero,
            gallery=[],
            booking_url=None,
            turnstile_site_key=settings.turnstile_site_key,
            enable_3d=fix.get("enable_3d", True),
            inventory=inventory,
            category_label=label,
        )
        site.site_spec = spec.model_dump(mode="json")
        assets = {
            "hero.svg": hero_svg(biz.name, palette["primary"], palette["accent"], spec.hero.model),
            "og.svg": hero_svg(
                biz.name, palette["primary"], palette["accent"], spec.hero.model, 1200, 630
            ),
        }
        site.status = GeneratedSiteStatus.DEPLOYING
        await ctx.db.commit()
        try:
            build = await build_site(settings, spec, assets, slug=slug, base_path=base_path)
        except BuildError as exc:
            history.append({"attempt": attempt, "error": str(exc)[:500]})
            continue
        deployed = await deployer.deploy(slug, build.out_dir, noindex=True)
        await record_usage(
            ctx.db,
            ApiProvider.VERCEL,
            "deploy",
            mocked=deployed.mocked,
            job_id=ctx.job.id,
            meta={"slug": slug},
        )
        site.preview_url = deployed.url
        site.vercel_project_id = deployed.project_id
        site.vercel_deployment_id = deployed.deployment_id
        await ctx.db.commit()

        audit = await run_audit(ctx, biz, deployed.url, generated_site_id=site.id)
        await ctx.db.commit()
        score = audit.total_score or 0
        parity = await page_inventory.check_parity(
            ctx.services.fetcher, deployed.url, inventory, spec
        )
        site.page_parity = parity
        ok, why = gate(score, baseline, parity["missing"])
        history.append(
            {
                "attempt": attempt,
                "builder": build.builder,
                "score": score,
                "first_load_js_kb": build.first_load_js_kb,
                "passed": ok,
                "reason": why,
                "audit_id": str(audit.id),
                "pages": f"{parity['present']}/{parity['expected']}",
                "fix": fix,
            }
        )
        site.score = score
        if ok:
            passed = True
            break

    site.failure_reason = None if passed else json.dumps(history)[-2000:]
    if passed:
        site.status = GeneratedSiteStatus.LIVE
        site.expires_at = datetime.now(UTC) + timedelta(days=settings.preview_ttl_days)
        biz.lead_status = LeadStatus.SITE_READY
    else:
        site.status = GeneratedSiteStatus.MANUAL_REVIEW
    await ctx.db.commit()

    if passed:
        await ctx.enqueue(
            JobQueue.EMAIL,
            "draft_outreach",
            f"draft:{biz.id}:{site.id}",
            {"business_id": str(biz.id), "generated_site_id": str(site.id)},
            business_id=biz.id,
        )
    return {
        "status": site.status.value,
        "preview_url": site.preview_url,
        "baseline": baseline,
        "score": site.score,
        "attempts": history,
        "page_parity": site.page_parity,
    }
