"""Headless Chromium checks: screenshots (1440 desktop + 390 mobile), horizontal
overflow at 360/390/768px, console errors, tap-target sizes and axe-core.

Optional: if Playwright or its browser is unavailable, audits fall back to static
HTML checks and record that the browser evidence is missing.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger("leadforge.browser")

AXE_JS = (Path(__file__).resolve().parent.parent / "assets" / "axe.min.js").read_text()

OVERFLOW_WIDTHS = (360, 390, 768)

# Returns (status, headers, body) for URLs the browser must not fetch from the network
# (mock sites, local previews), or None to let the request through.
RouteResolver = Callable[[str], tuple[int, dict[str, str], bytes] | None]

_MEASURE_JS = """
() => {
  const docW = document.documentElement.clientWidth;
  const overflow = document.documentElement.scrollWidth > docW + 1;
  const targets = [...document.querySelectorAll('a[href], button, input, select, textarea')]
    .filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
  const small = targets.filter(el => {
    const r = el.getBoundingClientRect(); return r.width < 24 || r.height < 24; }).length;
  const texts = [...document.querySelectorAll('p, li, a, span, td')].slice(0, 300);
  const tiny = texts.filter(el => parseFloat(getComputedStyle(el).fontSize) < 12).length;
  const foldCta = targets.some(el => {
    const r = el.getBoundingClientRect();
    const t = (el.innerText || el.value || '').toLowerCase();
    return r.top < window.innerHeight && /call|book|contact|appointment|enquir|quote|order|reserve|whatsapp/.test(t);
  });
  return { overflow, targets: targets.length, small_targets: small, text_nodes: texts.length,
           tiny_text: tiny, cta_above_fold: foldCta };
}
"""


@dataclass
class BrowserReport:
    available: bool
    screenshots: dict[str, bytes] = field(default_factory=dict)
    overflow: dict[int, bool] = field(default_factory=dict)
    mobile_metrics: dict[str, Any] = field(default_factory=dict)
    console_errors: list[str] = field(default_factory=list)
    axe_violations: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


class BrowserProbe:
    def __init__(self, resolver: RouteResolver | None = None, offline: bool = False) -> None:
        self.resolver = resolver
        self.offline = offline

    async def probe(self, url: str, *, screenshots: bool = True) -> BrowserReport:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return BrowserReport(available=False, error="playwright not installed")
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch()
                try:
                    return await self._run(browser, url, screenshots)
                finally:
                    await browser.close()
        except Exception as exc:  # browser missing, crash, navigation failure
            log.warning("browser probe failed", extra={"url": url, "error": str(exc)})
            return BrowserReport(available=False, error=f"{type(exc).__name__}: {exc}"[:500])

    async def _route(self, route: Any) -> None:
        req_url = route.request.url
        if self.resolver is not None:
            hit = self.resolver(req_url)
            if hit is not None:
                status, headers, body = hit
                await route.fulfill(status=status, headers=headers, body=body)
                return
        if self.offline:
            await route.abort()
            return
        await route.continue_()

    async def _run(self, browser: Any, url: str, screenshots: bool) -> BrowserReport:
        report = BrowserReport(available=True)
        for width in (*OVERFLOW_WIDTHS, 1440):
            mobile = width < 1024
            ctx = await browser.new_context(
                viewport={"width": width, "height": 844 if mobile else 900},
                device_scale_factor=1,
                is_mobile=mobile,
                has_touch=mobile,
                reduced_motion="reduce",
                bypass_csp=True,
            )
            await ctx.route("**/*", self._route)
            page = await ctx.new_page()
            if width == 390:
                page.on(
                    "console",
                    lambda m: (
                        report.console_errors.append(m.text[:300]) if m.type == "error" else None
                    ),
                )
                page.on("pageerror", lambda e: report.console_errors.append(str(e)[:300]))
            await page.goto(url, wait_until="load", timeout=30_000)
            await page.wait_for_timeout(300)
            metrics = await page.evaluate(_MEASURE_JS)
            if width in OVERFLOW_WIDTHS:
                report.overflow[width] = bool(metrics["overflow"])
            if width == 390:
                report.mobile_metrics = metrics
                await page.add_script_tag(content=AXE_JS)
                axe = await page.evaluate(
                    "async () => (await axe.run(document, {resultTypes: ['violations']})).violations"
                    ".map(v => ({id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length}))"
                )
                report.axe_violations = axe
            if screenshots and width in (390, 1440):
                report.screenshots[
                    "mobile_390" if width == 390 else "desktop_1440"
                ] = await page.screenshot(full_page=False, type="png")
            await ctx.close()
        return report
