"""LeadForge website scoring rubric. Deterministic and versioned.

The same scorer runs on prospects' sites and on the sites we generate. Bump
RUBRIC_VERSION whenever a weight, threshold or check changes; audits record it.
"""

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from leadforge.clients.browser import BrowserReport
from leadforge.clients.psi import PsiResult
from leadforge.scoring.signals import PageSignals

RUBRIC_VERSION = "1.0.0"

CATEGORY_MAX = {
    "performance": 20,
    "seo": 15,
    "mobile": 15,
    "design": 15,
    "accessibility": 10,
    "trust": 10,
    "conversion": 10,
    "tech": 5,
}
CATEGORY_LABEL = {
    "performance": "Performance",
    "seo": "SEO",
    "mobile": "Mobile & responsive",
    "design": "Visual design",
    "accessibility": "Accessibility",
    "trust": "Trust & security",
    "conversion": "Conversion",
    "tech": "Tech health",
}
DESIGN_CRITERIA = (
    "modernity", "typography", "spacing", "colour", "hierarchy", "imagery", "consistency",
)  # fmt: skip


@dataclass
class Check:
    id: str
    category: str
    max_points: float
    earned: float
    issue: str | None = None  # plain-language, shown to the owner when points are lost
    evidence: Any = None

    @property
    def lost(self) -> float:
        return self.max_points - self.earned


@dataclass
class AuditInputs:
    url: str
    final_url: str
    status: int
    headers: dict[str, str]
    signals: PageSignals
    psi_mobile: PsiResult | None
    psi_desktop: PsiResult | None
    browser: BrowserReport | None
    design_scores: dict[str, float] | None  # 0..5 per DESIGN_CRITERIA
    design_rationale: str | None
    has_sitemap: bool
    robots_txt_ok: bool
    broken_links: int
    links_checked: int
    business_name: str
    phone_digits: str
    page_text: str
    year: int
    # Generated previews are deliberately noindex until the client buys; score them as launched.
    preview: bool = False


@dataclass
class ScoreResult:
    total: int
    grade: str
    breakdown: dict[str, dict[str, float]]
    checks: list[Check] = field(default_factory=list)
    top_issues: list[str] = field(default_factory=list)
    rubric_version: str = RUBRIC_VERSION


def grade_for(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 50:
        return "C"
    return "D"


def _tier(value: float | None, good: float, ok: float) -> float:
    """1.0 if value <= good, 0.5 if <= ok, else 0. None counts as 0.5 (unknown)."""
    if value is None:
        return 0.5
    if value <= good:
        return 1.0
    if value <= ok:
        return 0.5
    return 0.0


def _perf_checks(i: AuditInputs) -> list[Check]:
    out: list[Check] = []
    m, d = i.psi_mobile, i.psi_desktop

    def blended(f: Any) -> float:
        vals = [(0.7, f(m)) if m else None, (0.3, f(d)) if d else None]
        present = [v for v in vals if v]
        if not present:
            return 0.5
        weight = sum(w for w, _ in present)
        return float(sum(w * v for w, v in present) / weight)

    lcp_s = (m.lcp_ms / 1000) if m and m.lcp_ms else None
    out.append(
        Check(
            "perf.lcp",
            "performance",
            6,
            6 * blended(lambda r: _tier(r.lcp_ms, 2500, 4000)),
            f"Your site takes {lcp_s:.1f}s to show its main content on phones (aim for under 2.5s)"
            if lcp_s and lcp_s > 2.5
            else None,
            {"mobile_lcp_ms": m.lcp_ms if m else None, "desktop_lcp_ms": d.lcp_ms if d else None},
        )
    )
    out.append(
        Check(
            "perf.interactivity",
            "performance",
            4,
            4
            * blended(
                lambda r: _tier(
                    r.inp_ms if r.inp_ms is not None else r.tbt_ms,
                    200,
                    500 if r.inp_ms is not None else 600,
                )
            ),
            "Taps and clicks feel sluggish because heavy scripts block the page"
            if m and (m.tbt_ms or 0) > 600
            else None,
            {"mobile_tbt_ms": m.tbt_ms if m else None, "mobile_inp_ms": m.inp_ms if m else None},
        )
    )
    out.append(
        Check(
            "perf.cls",
            "performance",
            4,
            4 * blended(lambda r: _tier(r.cls, 0.1, 0.25)),
            "Content jumps around while the page loads, which makes visitors mis-tap"
            if m and (m.cls or 0) > 0.1
            else None,
            {"mobile_cls": m.cls if m else None},
        )
    )
    mb = (m.total_bytes / 1_000_000) if m and m.total_bytes else None
    out.append(
        Check(
            "perf.weight",
            "performance",
            3,
            3 * _tier(mb, 1.5, 3.0),
            f"Your homepage downloads {mb:.1f} MB, which is slow and costly on mobile data"
            if mb and mb > 3.0
            else None,
            {"total_mb": round(mb, 2) if mb else None},
        )
    )
    out.append(
        Check(
            "perf.lighthouse",
            "performance",
            3,
            3
            * blended(
                lambda r: 1.0 if r.performance >= 0.9 else 0.5 if r.performance >= 0.5 else 0.0
            ),
            None,
            {"mobile": m.performance if m else None, "desktop": d.performance if d else None},
        )
    )
    return out


def _seo_checks(i: AuditInputs) -> list[Check]:
    s = i.signals
    title_ok = bool(s.title) and 10 <= len(s.title or "") <= 65
    desc_ok = bool(s.meta_description) and 50 <= len(s.meta_description or "") <= 170
    alt_ratio = (s.images_with_alt / s.images) if s.images else 1.0
    return [
        Check(
            "seo.title",
            "seo",
            2,
            2 if title_ok else (1 if s.title else 0),
            None if title_ok else "Your page title doesn't tell Google what you do and where",
            {"title": s.title},
        ),
        Check(
            "seo.description",
            "seo",
            2,
            2 if desc_ok else (1 if s.meta_description else 0),
            None
            if desc_ok
            else "Google has no description to show under your link in search results",
            {"description": s.meta_description},
        ),
        Check(
            "seo.h1",
            "seo",
            2,
            2 if s.h1_count == 1 else (1 if s.h1_count > 1 else 0),
            None if s.h1_count else "Your homepage has no main heading for search engines to read",
            {"h1_count": s.h1_count},
        ),
        Check("seo.canonical", "seo", 1, 1 if s.canonical else 0, None, {"canonical": s.canonical}),
        Check("seo.sitemap", "seo", 1, 1 if i.has_sitemap else 0, None, {"sitemap": i.has_sitemap}),
        Check(
            "seo.robots",
            "seo",
            1,
            1 if i.robots_txt_ok or i.preview else 0,
            None,
            {"robots_ok": i.robots_txt_ok, "preview": i.preview},
        ),
        Check(
            "seo.schema",
            "seo",
            2,
            2 if s.has_local_business_schema else 0,
            None
            if s.has_local_business_schema
            else "Google can't read your address, hours and phone as structured business data",
            {"jsonld_types": s.jsonld_types},
        ),
        Check(
            "seo.og",
            "seo",
            1,
            (0.5 if s.og_title else 0) + (0.5 if s.og_image else 0),
            None
            if s.og_image
            else "Links to your site shared on WhatsApp or Facebook show no preview image",
            {"og_title": s.og_title, "og_image": s.og_image},
        ),
        Check(
            "seo.alt",
            "seo",
            2,
            2 * (1.0 if alt_ratio >= 0.9 else alt_ratio),
            None
            if alt_ratio >= 0.9
            else f"{s.images - s.images_with_alt} images have no text description for search engines",
            {"images": s.images, "with_alt": s.images_with_alt},
        ),
        Check(
            "seo.indexable",
            "seo",
            1,
            1
            if i.preview
            else 0
            if s.noindex or "noindex" in i.headers.get("x-robots-tag", "")
            else 1,
            "Your site tells Google not to list it in search results"
            if s.noindex and not i.preview
            else None,
            {"noindex": s.noindex, "preview": i.preview},
        ),
    ]


def _mobile_checks(i: AuditInputs) -> list[Check]:
    s, b = i.signals, i.browser
    browser_ok = b is not None and b.available
    if browser_ok:
        assert b is not None
        overflow_widths = [w for w, o in b.overflow.items() if o]
        overflow_score = 1 - len(overflow_widths) / max(1, len(b.overflow))
        mm = b.mobile_metrics
        small_ratio = (mm.get("small_targets", 0) / mm["targets"]) if mm.get("targets") else 0
        tap_score = 1.0 if small_ratio <= 0.1 else 0.5 if small_ratio <= 0.3 else 0.0
        tiny_ratio = (mm.get("tiny_text", 0) / mm["text_nodes"]) if mm.get("text_nodes") else 0
        font_score = 1.0 if tiny_ratio <= 0.05 else 0.5 if tiny_ratio <= 0.2 else 0.0
        evidence: dict[str, Any] = {"overflow": b.overflow, "metrics": mm}
    else:
        wide = (s.fixed_width_px or 0) > 400 or s.table_layout
        overflow_widths = [360, 390] if wide or not s.viewport else []
        overflow_score = 0.0 if overflow_widths else 1.0
        tap_score = 0.5 if s.viewport else 0.0
        font_score = 0.0 if (s.font_tags or s.tiny_inline_fonts) else (1.0 if s.viewport else 0.5)
        evidence = {"static_fallback": True, "fixed_width_px": s.fixed_width_px}
    return [
        Check(
            "mobile.viewport",
            "mobile",
            4,
            4 if s.viewport else 0,
            None
            if s.viewport
            else "Your site isn't set up for phones, so visitors have to pinch and zoom",
            {"viewport": s.viewport},
        ),
        Check(
            "mobile.overflow",
            "mobile",
            5,
            5 * overflow_score,
            None
            if not overflow_widths
            else "Parts of your page spill off the side of the screen on phones",
            evidence,
        ),
        Check(
            "mobile.tap_targets",
            "mobile",
            3,
            3 * tap_score,
            None
            if tap_score >= 1
            else "Buttons and links are too small or close together to tap easily",
            None,
        ),
        Check(
            "mobile.font_size",
            "mobile",
            3,
            3 * font_score,
            None if font_score >= 1 else "Text is too small to read on a phone without zooming",
            None,
        ),
    ]


def _design_checks(i: AuditInputs) -> list[Check]:
    scores = i.design_scores or {}
    checks: list[Check] = []
    per = 15 / len(DESIGN_CRITERIA)
    for crit in DESIGN_CRITERIA:
        v = max(0.0, min(5.0, float(scores.get(crit, 2.5))))
        checks.append(Check(f"design.{crit}", "design", per, per * v / 5, None, {"score_0_5": v}))
    avg = sum(c.earned for c in checks) / 15 * 5
    if avg < 3:
        checks[
            0
        ].issue = (
            "The design looks dated next to competitors, which costs trust in the first few seconds"
        )
    checks[0].evidence = {"score_0_5": scores.get("modernity"), "rationale": i.design_rationale}
    return checks


def _a11y_checks(i: AuditInputs) -> list[Check]:
    s, b = i.signals, i.browser
    lh = (
        i.psi_mobile.accessibility
        if i.psi_mobile and i.psi_mobile.accessibility is not None
        else None
    )
    serious = 0
    if b is not None and b.available:
        serious = sum(1 for v in b.axe_violations if v.get("impact") in ("serious", "critical"))
    axe_score = 1.0 if serious == 0 else 0.5 if serious <= 3 else 0.0
    base = (
        (lh if lh is not None else 0.6) * 0.5 + axe_score * 0.5
        if b and b.available
        else (lh if lh is not None else 0.6)
    )
    alt_ok = (s.images_with_alt / s.images) >= 0.9 if s.images else True
    labels_ok = s.form_inputs == 0 or s.form_labels >= s.form_inputs
    names_ok = s.unnamed_links == 0 and s.unnamed_buttons == 0
    return [
        Check(
            "a11y.lighthouse_axe",
            "accessibility",
            6,
            6 * base,
            "People using screen readers or keyboard navigation will struggle with your site"
            if base < 0.7
            else None,
            {
                "lighthouse": lh,
                "axe_serious": serious,
                "axe": (b.axe_violations[:10] if b and b.available else None),
            },
        ),
        Check("a11y.lang", "accessibility", 1, 1 if s.lang else 0, None, {"lang": s.lang}),
        Check("a11y.alt", "accessibility", 1, 1 if alt_ok else 0, None, None),
        Check("a11y.labels", "accessibility", 1, 1 if labels_ok else 0, None, None),
        Check(
            "a11y.names",
            "accessibility",
            1,
            1 if names_ok else 0,
            None,
            {"unnamed_links": s.unnamed_links, "unnamed_buttons": s.unnamed_buttons},
        ),
    ]


def _trust_checks(i: AuditInputs) -> list[Check]:
    s, h = i.signals, i.headers
    # Local mock previews are served over plain HTTP by the dev API; every real deploy target
    # (Vercel) is HTTPS-only, so that's a property of the host, not of the generated site.
    local_preview = i.preview and urlsplit(i.final_url).hostname in (
        "localhost",
        "127.0.0.1",
        "test",
    )
    https = i.final_url.startswith("https://") or local_preview
    sec = sum(
        1
        for k in ("strict-transport-security", "content-security-policy", "x-content-type-options")
        if k in h
    )
    text = i.page_text.lower()
    name_shown = bool(i.business_name) and i.business_name.lower()[:12] in text
    phone_shown = bool(i.phone_digits) and i.phone_digits[-6:] in "".join(
        ch for ch in text if ch.isdigit()
    )
    nap = (1 if name_shown or s.title else 0) + (1 if phone_shown or s.tel_links else 0)
    fresh = s.copyright_year is not None and s.copyright_year >= i.year - 1
    return [
        Check(
            "trust.https",
            "trust",
            3,
            3 if https else 0,
            None
            if https
            else "Browsers mark your site 'Not secure' because it has no SSL certificate",
            {"final_url": i.final_url, "local_preview": local_preview},
        ),
        Check("trust.headers", "trust", 2, 2 * sec / 3, None, {"security_headers": sec}),
        Check(
            "trust.privacy",
            "trust",
            1,
            1 if s.privacy_link else 0,
            None
            if s.privacy_link
            else "There's no privacy policy, which visitors and Google look for",
            None,
        ),
        Check(
            "trust.nap",
            "trust",
            2,
            nap,
            None if nap >= 2 else "Your phone number isn't clearly visible on the homepage",
            None,
        ),
        Check(
            "trust.social_proof",
            "trust",
            1,
            1 if s.testimonials else 0,
            None
            if s.testimonials
            else "Your site doesn't show any reviews, even though customers rate you on Google",
            None,
        ),
        Check(
            "trust.freshness",
            "trust",
            1,
            1 if fresh else 0,
            None
            if fresh or s.copyright_year is None
            else f"The footer still says © {s.copyright_year}, so the site looks abandoned",
            {"copyright_year": s.copyright_year},
        ),
    ]


def _conversion_checks(i: AuditInputs) -> list[Check]:
    s, b = i.signals, i.browser
    cta = (
        b.mobile_metrics.get("cta_above_fold")
        if b and b.available and b.mobile_metrics
        else s.cta_early
    )
    return [
        Check(
            "conv.cta",
            "conversion",
            2,
            2 if cta else 0,
            None if cta else "There's no clear 'Call' or 'Book' button when the page first opens",
            None,
        ),
        Check(
            "conv.click_to_call",
            "conversion",
            2,
            2 if s.tel_links else 0,
            None if s.tel_links else "Phone visitors can't tap to call you",
            {"tel_links": s.tel_links},
        ),
        Check(
            "conv.channel",
            "conversion",
            2,
            2 if (s.whatsapp or s.booking or s.form) else 0,
            None
            if (s.whatsapp or s.booking or s.form)
            else "There's no WhatsApp, booking or enquiry form, so leads have to call or leave",
            {"whatsapp": s.whatsapp, "booking": s.booking, "form": s.form},
        ),
        Check("conv.map", "conversion", 1, 1 if s.map_embed else 0, None, None),
        Check(
            "conv.hours",
            "conversion",
            1,
            1 if s.hours_text else 0,
            None if s.hours_text else "Your opening hours aren't on the site",
            None,
        ),
        Check("conv.pricing", "conversion", 1, 1 if s.pricing_text else 0, None, None),
        Check("conv.contact", "conversion", 1, 1 if (s.email_visible or s.form) else 0, None, None),
    ]


def _tech_checks(i: AuditInputs) -> list[Check]:
    s, b = i.signals, i.browser
    broken_ratio = i.broken_links / i.links_checked if i.links_checked else 0
    errors = len(b.console_errors) if b and b.available else None
    heavy_js = s.inline_script_bytes > 300_000 or s.external_scripts > 25
    return [
        Check(
            "tech.broken_links",
            "tech",
            2,
            2 * (1 if i.broken_links == 0 else 0.5 if broken_ratio < 0.2 else 0),
            None
            if i.broken_links == 0
            else f"{i.broken_links} links on your site lead to error pages",
            {"broken": i.broken_links, "checked": i.links_checked},
        ),
        Check(
            "tech.stack",
            "tech",
            1,
            0 if s.outdated_markers else 1,
            None
            if not s.outdated_markers
            else "Your site runs on outdated code that modern browsers struggle with",
            {"markers": s.outdated_markers},
        ),
        Check(
            "tech.console",
            "tech",
            1,
            0.5 if errors is None else (1 if errors == 0 else 0),
            None,
            {"console_errors": (b.console_errors[:5] if b and b.available else None)},
        ),
        Check(
            "tech.bloat",
            "tech",
            1,
            0 if (s.builder or heavy_js) else 1,
            None,
            {"builder": s.builder, "external_scripts": s.external_scripts},
        ),
    ]


def score(i: AuditInputs) -> ScoreResult:
    checks = (
        _perf_checks(i)
        + _seo_checks(i)
        + _mobile_checks(i)
        + _design_checks(i)
        + _a11y_checks(i)
        + _trust_checks(i)
        + _conversion_checks(i)
        + _tech_checks(i)
    )
    breakdown: dict[str, dict[str, float]] = {}
    for cat, cap in CATEGORY_MAX.items():
        earned = sum(c.earned for c in checks if c.category == cat)
        breakdown[cat] = {"score": round(min(earned, cap), 1), "max": cap}
    total = round(sum(v["score"] for v in breakdown.values()))
    issues = sorted((c for c in checks if c.issue and c.lost > 0), key=lambda c: -c.lost)
    top: list[str] = []
    for c in issues:
        if c.issue and c.issue not in top:
            top.append(c.issue)
        if len(top) == 5:
            break
    return ScoreResult(
        total=total, grade=grade_for(total), breakdown=breakdown, checks=checks, top_issues=top
    )


def no_website_result(category_label: str, city: str) -> ScoreResult:
    breakdown = {cat: {"score": 0.0, "max": cap} for cat, cap in CATEGORY_MAX.items()}
    return ScoreResult(
        total=0,
        grade="D",
        breakdown=breakdown,
        top_issues=[
            f"You don't have a website, so people searching for {category_label.lower()} in {city} can't find you",
            "Customers can't see your services, hours or prices before they call",
            "There's no way to book or send an enquiry online, day or night",
        ],
    )
