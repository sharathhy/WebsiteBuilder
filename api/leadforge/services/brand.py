"""Brand colour extraction from a business's existing site, with category fallbacks."""

import colorsys
import re
from collections import Counter

HEX_RE = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
RGB_RE = re.compile(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})")

# (primary, secondary, accent) per template, chosen for AA contrast on white.
FALLBACK_PALETTES: dict[str, tuple[str, str, str]] = {
    "clinic": ("#0e7490", "#0f172a", "#22c55e"),
    "restaurant": ("#b45309", "#1c1917", "#dc2626"),
    "salon": ("#9d174d", "#1f1720", "#d4a373"),
    "fitness": ("#dc2626", "#0a0a0a", "#facc15"),
    "legal-finance": ("#1e3a8a", "#0f172a", "#b8860b"),
    "real-estate": ("#065f46", "#111827", "#d97706"),
    "home-services": ("#1d4ed8", "#111827", "#f59e0b"),
    "generic-premium": ("#4338ca", "#0f172a", "#06b6d4"),
}


def _norm(h: str) -> str:
    h = h.lower().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return f"#{h}"


def _hls(hexstr: str) -> tuple[float, float, float]:
    r, g, b = (int(hexstr[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)


def luminance(hexstr: str) -> float:
    def ch(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hexstr[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def darken_for_contrast(hexstr: str, against: str = "#ffffff", target: float = 4.5) -> str:
    h, lum, s = _hls(hexstr)
    while contrast(hexstr, against) < target and lum > 0.05:
        lum -= 0.04
        r, g, b = colorsys.hls_to_rgb(h, max(lum, 0), s)
        hexstr = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
    return hexstr


def extract_brand_colors(html: str | None) -> list[str]:
    """Most frequent saturated colours on the page (theme-color first)."""
    if not html:
        return []
    found: list[str] = []
    theme = re.search(
        r'<meta[^>]+name=["\']theme-color["\'][^>]+content=["\'](#[0-9a-fA-F]{3,6})', html
    )
    if theme:
        found.append(_norm(theme.group(1)))
    counts: Counter[str] = Counter(_norm("#" + m) for m in HEX_RE.findall(html))
    for r, g, b in RGB_RE.findall(html):
        counts["#{:02x}{:02x}{:02x}".format(*(min(255, int(x)) for x in (r, g, b)))] += 1
    for color, _ in counts.most_common(30):
        _, lum, sat = _hls(color)
        if sat >= 0.35 and 0.15 <= lum <= 0.75 and color not in found:
            found.append(color)
    return found[:3]


def build_palette(template: str, html: str | None) -> dict[str, str]:
    primary, secondary, accent = FALLBACK_PALETTES.get(
        template, FALLBACK_PALETTES["generic-premium"]
    )
    brand = extract_brand_colors(html)
    if brand:
        primary = brand[0]
        if len(brand) > 1:
            accent = brand[1]
    return {
        "primary": darken_for_contrast(primary),
        "secondary": secondary,
        "accent": accent,
        "background": "#ffffff",
        "foreground": "#0f172a",
        "source": "site" if brand else "category_default",
    }
