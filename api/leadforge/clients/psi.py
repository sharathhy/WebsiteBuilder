"""PageSpeed Insights (Lighthouse) for mobile + desktop, and a deterministic mock."""

import re
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

import httpx

PSI_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
Strategy = Literal["mobile", "desktop"]


@dataclass
class PsiResult:
    strategy: Strategy
    performance: float  # 0..1
    accessibility: float | None
    lcp_ms: float | None
    cls: float | None
    tbt_ms: float | None
    inp_ms: float | None  # field data (CrUX) when available
    total_bytes: int | None
    raw_audits: dict[str, Any] = field(default_factory=dict)
    mocked: bool = False


class PsiClient(Protocol):
    async def run(self, url: str, strategy: Strategy, html: str | None = None) -> PsiResult: ...


def _num(audits: dict[str, Any], key: str) -> float | None:
    v = audits.get(key, {}).get("numericValue")
    return float(v) if v is not None else None


class GooglePsiClient:
    def __init__(self, api_key: str | None, client: httpx.AsyncClient | None = None) -> None:
        self.api_key = api_key
        self.client = client or httpx.AsyncClient(timeout=120)

    async def run(self, url: str, strategy: Strategy, html: str | None = None) -> PsiResult:
        params: list[tuple[str, str | int | float | bool | None]] = [
            ("url", url),
            ("strategy", strategy),
        ]
        params += [("category", c) for c in ("performance", "accessibility", "seo")]
        if self.api_key:
            params.append(("key", self.api_key))
        resp = await self.client.get(PSI_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        lh = data["lighthouseResult"]
        audits = lh["audits"]
        cats = lh["categories"]
        field_inp = (
            data.get("loadingExperience", {})
            .get("metrics", {})
            .get("INTERACTION_TO_NEXT_PAINT", {})
            .get("percentile")
        )
        keep = ("viewport", "font-size", "tap-targets", "is-crawlable", "document-title")
        return PsiResult(
            strategy=strategy,
            performance=float(cats["performance"]["score"] or 0),
            accessibility=float(cats.get("accessibility", {}).get("score") or 0),
            lcp_ms=_num(audits, "largest-contentful-paint"),
            cls=_num(audits, "cumulative-layout-shift"),
            tbt_ms=_num(audits, "total-blocking-time"),
            inp_ms=float(field_inp) if field_inp is not None else None,
            total_bytes=int(_num(audits, "total-byte-weight") or 0),
            raw_audits={k: audits[k].get("score") for k in keep if k in audits},
        )


class MockPsiClient:
    """Derives plausible, deterministic Lighthouse-like numbers from the page itself.

    Same HTML in, same numbers out, so mock audits are exactly reproducible.
    """

    def __init__(self, asset_bytes: Any = None) -> None:
        # Optional callable(url) -> int, total bytes of JS/CSS/images for local previews.
        self.asset_bytes = asset_bytes

    async def run(self, url: str, strategy: Strategy, html: str | None = None) -> PsiResult:
        html = html or ""
        low = html.lower()
        imgs = len(re.findall(r"<img\b", low))
        scripts = len(re.findall(r"<script\b[^>]*\bsrc=", low))
        legacy = sum(k in low for k in ("jquery-1.", "<table", "<font", "bgcolor"))
        has_viewport = 'name="viewport"' in low
        modern = "<!doctype html>" in low
        sized_imgs = len(re.findall(r"<img\b[^>]*\bwidth=", low))
        extra = self.asset_bytes(url) if self.asset_bytes else None
        total = extra if extra is not None else len(html) + imgs * 380_000 + scripts * 95_000
        mobile = strategy == "mobile"
        lcp = 900 + total / (1_400 if mobile else 6_000) + legacy * (900 if mobile else 300)
        if not has_viewport and mobile:
            lcp += 1_500
        tbt = scripts * (180 if mobile else 60) + legacy * (120 if mobile else 30)
        cls = 0.02 + max(0, imgs - sized_imgs) * 0.09 + (0.05 if not modern else 0)
        perf = max(
            0.05,
            min(
                1.0,
                1.0 - max(0, lcp - 1_200) / 9_000 - tbt / 3_000 - min(cls, 0.5) * 0.6,
            ),
        )
        a11y = max(0.3, min(1.0, 0.98 - legacy * 0.12 - (0 if modern else 0.1)))
        return PsiResult(
            strategy=strategy,
            performance=round(perf, 2),
            accessibility=round(a11y, 2),
            lcp_ms=round(lcp),
            cls=round(cls, 3),
            tbt_ms=round(tbt),
            inp_ms=None,
            total_bytes=int(total),
            raw_audits={"viewport": 1 if has_viewport else 0},
            mocked=True,
        )
