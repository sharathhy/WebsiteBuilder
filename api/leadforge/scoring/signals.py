"""Static HTML signals used by the rubric. Pure functions of the fetched page."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from leadforge.services.contacts import jsonld_types

LOCAL_BUSINESS_TYPES = {
    "LocalBusiness", "Dentist", "MedicalClinic", "Physician", "Restaurant", "CafeOrCoffeeShop",
    "BeautySalon", "DaySpa", "HairSalon", "HealthClub", "ExerciseGym", "LegalService",
    "Attorney", "AccountingService", "RealEstateAgent", "HomeAndConstructionBusiness",
    "AutoRepair", "Hotel", "LodgingBusiness", "EducationalOrganization", "ProfessionalService",
    "MedicalBusiness", "FoodEstablishment", "Store",
}  # fmt: skip
CTA_RE = re.compile(
    r"\b(call|book|contact|appointment|enquir|quote|order|reserve|whatsapp|get started|visit)",
    re.I,
)
OUTDATED_RE = re.compile(
    r"jquery[-.]1\.|jquery[-.]2\.|swfobject|\.swf\b|best viewed in|internet explorer|<marquee|"
    r"<font\b|<center\b|bgcolor=",
    re.I,
)
BUILDERS = ("wix.com", "squarespace", "weebly", "godaddy website builder", "jimdo", "elementor")


@dataclass
class PageSignals:
    title: str | None
    meta_description: str | None
    h1_count: int
    canonical: bool
    og_title: bool
    og_image: bool
    noindex: bool
    lang: bool
    viewport: bool
    images: int
    images_with_alt: int
    images_sized: int
    jsonld_types: list[str]
    has_local_business_schema: bool
    tel_links: int
    whatsapp: bool
    booking: bool
    form: bool
    form_inputs: int
    form_labels: int
    map_embed: bool
    hours_text: bool
    pricing_text: bool
    privacy_link: bool
    testimonials: bool
    copyright_year: int | None
    cta_early: bool
    email_visible: bool
    unnamed_links: int
    unnamed_buttons: int
    table_layout: bool
    font_tags: bool
    tiny_inline_fonts: bool
    fixed_width_px: int | None
    outdated_markers: list[str]
    builder: str | None
    inline_script_bytes: int
    external_scripts: int
    internal_links: list[str] = field(default_factory=list)
    text_length: int = 0


def analyze(html: str, url: str, business_name: str = "", phone_digits: str = "") -> PageSignals:
    soup = BeautifulSoup(html or "", "lxml")
    low = (html or "").lower()
    text = soup.get_text(" ", strip=True)
    text_low = text.lower()

    def meta(name: str, attr: str = "name") -> str | None:
        tag = soup.find("meta", attrs={attr: re.compile(f"^{re.escape(name)}$", re.I)})
        if not isinstance(tag, Tag) or not tag.get("content"):
            return None
        return str(tag.get("content")).strip()

    robots_meta = (meta("robots") or "").lower()
    imgs = soup.find_all("img")
    types = jsonld_types(html or "")
    body = soup.body
    early_text = ""
    early_links: list[Any] = []
    if body:
        early_links = body.find_all(["a", "button"], limit=12)
        early_text = " ".join(el.get_text(" ", strip=True) for el in early_links)
    years = [
        int(y) for y in re.findall(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?(\d{4})", low)
    ]

    host = urlsplit(url).netloc.lower()
    internal: list[str] = []
    for a in soup.find_all("a", href=True):
        href = urljoin(url, str(a["href"])).split("#", 1)[0]
        parts = urlsplit(href)
        if (
            parts.scheme in ("http", "https")
            and parts.netloc.lower() == host
            and href not in internal
        ):
            internal.append(href)

    # Fixed layout widths (tables/containers or inline styles). <img width> is intrinsic size.
    widths = [
        int(w)
        for w in re.findall(r'<(?:table|td|div|body)\b[^>]*\bwidth\s*=\s*["\']?(\d{3,4})', low)
    ]
    widths += [int(w) for w in re.findall(r"(?<![-\w])width\s*:\s*(\d{3,4})px", low)]
    inline_js = sum(len(s.string or "") for s in soup.find_all("script") if not s.get("src"))
    generator = (meta("generator") or "").lower()
    builder = next((b for b in BUILDERS if b in generator or b in low[:50_000]), None)
    labels = len(soup.find_all("label")) + len(
        soup.select("input[aria-label], textarea[aria-label]")
    )

    return PageSignals(
        title=soup.title.get_text(strip=True) if soup.title else None,
        meta_description=meta("description"),
        h1_count=len(soup.find_all("h1")),
        canonical=bool(soup.find("link", rel=lambda v: v and "canonical" in v)),
        og_title=bool(meta("og:title", "property")),
        og_image=bool(meta("og:image", "property")),
        noindex="noindex" in robots_meta,
        lang=bool(soup.html and soup.html.get("lang")),
        viewport=bool(meta("viewport")) and "width=device-width" in (meta("viewport") or ""),
        images=len(imgs),
        images_with_alt=sum(
            1
            for i in imgs
            if (i.get("alt") is not None and str(i.get("alt")).strip() != "")
            or (i.get("alt") == "" and i.get("role") == "presentation")
        ),
        images_sized=sum(1 for i in imgs if i.get("width") and i.get("height")),
        jsonld_types=types,
        has_local_business_schema=any(t in LOCAL_BUSINESS_TYPES for t in types),
        tel_links=len(soup.select('a[href^="tel:" i]')),
        whatsapp=any(k in low for k in ("wa.me/", "api.whatsapp.com", "whatsapp://")),
        booking=any(
            k in low
            for k in (
                "cal.com",
                "calendly",
                "practo",
                "zocdoc",
                "opentable",
                "booksy",
                "fresha",
                "/book",
                "book now",
                "book an appointment",
            )
        ),
        form=bool(soup.find("form")),
        form_inputs=len(soup.select("form input:not([type=hidden]), form textarea, form select")),
        form_labels=labels,
        map_embed=bool(
            re.search(
                r"google\.[a-z.]+/maps|maps\.google|maps\.app\.goo\.gl|mapbox|openstreetmap", low
            )
        ),
        hours_text=bool(
            re.search(r"\b(hours|open(ing)? times?|mon(day)?\s*[-–to]+\s*(fri|sat|sun))", text_low)
        ),
        pricing_text=bool(
            re.search(r"(pricing|price list|menu|rates|packages|₹\s?\d|\$\s?\d)", text_low)
        ),
        privacy_link=bool(soup.find("a", string=re.compile("privacy", re.I))) or "/privacy" in low,
        testimonials=bool(
            re.search(
                r"testimonial|reviews?|what (our )?(clients|patients|customers) say|★", text_low
            )
        ),
        copyright_year=max(years) if years else None,
        cta_early=bool(CTA_RE.search(early_text)),
        email_visible="mailto:" in low or bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)),
        unnamed_links=sum(
            1
            for a in soup.find_all("a", href=True)
            if not a.get_text(strip=True)
            and not a.get("aria-label")
            and not a.find("img", alt=True)
        ),
        unnamed_buttons=sum(
            1
            for b in soup.find_all("button")
            if not b.get_text(strip=True) and not b.get("aria-label")
        ),
        table_layout=bool(soup.find("table", attrs={"width": True})),
        font_tags=bool(soup.find("font")),
        tiny_inline_fonts=bool(re.search(r"font-size\s*:\s*(?:[0-9]|1[01])px", low)),
        fixed_width_px=max(widths) if widths else None,
        outdated_markers=sorted({m.group(0).lower() for m in OUTDATED_RE.finditer(html or "")}),
        builder=builder,
        inline_script_bytes=inline_js,
        external_scripts=len(soup.select("script[src]")),
        internal_links=internal[:50],
        text_length=len(text),
    )


def current_year() -> int:
    return datetime.now(UTC).year
