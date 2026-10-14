"""Deterministic fake businesses and websites for MOCK_APIS mode, tests and demos.

Everything here is obviously fictional: names start with "Sample", websites use the
reserved `.example` TLD, US phones use the 555-01xx fictional range and Indian phones
use a 0000 block. Nothing describes a real business.
"""

import hashlib
import random
from dataclasses import dataclass
from typing import Any, Literal

Quality = Literal["none", "poor", "dated", "decent", "good", "parked", "challenge"]

# Weighted so a typical city x category has roughly 25% no-website leads,
# ~45% weak sites (rebuild candidates) and the rest reasonable.
_QUALITY_WEIGHTS: list[tuple[Quality, int]] = [
    ("none", 25),
    ("poor", 25),
    ("dated", 20),
    ("decent", 15),
    ("good", 10),
    ("parked", 3),
    ("challenge", 2),
]

_NAME_PARTS = {
    "dentists": ("Dental Studio", "Smile Clinic", "Dental Care", "Family Dentistry"),
    "restaurants": ("Kitchen", "Bistro", "Eatery", "Grill"),
    "salons-spas": ("Salon", "Spa & Salon", "Beauty Lounge", "Hair Studio"),
}
_DEFAULT_PARTS = ("Studio", "Co.", "Services", "Associates")


@dataclass(frozen=True)
class MockBusiness:
    place_id: str
    name: str
    category: str
    city: str
    state: str
    country: str
    lat: float
    lng: float
    phone_international: str
    website: str | None
    quality: Quality
    rating: float
    review_count: int
    seq: int

    @property
    def domain(self) -> str | None:
        if not self.website:
            return None
        return self.website.split("//", 1)[1].split("/", 1)[0]


def site_slug(seq: int, category_id: str, city_id: str, country: str) -> str:
    return f"sample-{seq:02d}--{category_id}--{city_id}--{country.lower()}"


# 555-0100..0199 is reserved for fiction in every US area code; one area code per category
# keeps numbers unique across categories in the same city.
_US_AREA_CODES = (
    "512", "737", "210", "214", "713", "312", "646", "213",
    "602", "619", "408", "415", "305", "206", "617", "404",
)  # fmt: skip
_CATEGORY_ORDER = (
    "dentists", "restaurants", "salons-spas", "cafes", "clinics", "gyms", "real-estate",
    "lawyers", "accountants", "interior-designers", "wedding-planners", "auto-repair",
    "coaching-centres", "boutique-hotels",
)  # fmt: skip


def _category_index(category_id: str) -> int:
    if category_id in _CATEGORY_ORDER:
        return _CATEGORY_ORDER.index(category_id)
    return len(_CATEGORY_ORDER) + int(hashlib.sha256(category_id.encode()).hexdigest()[:4], 16) % 2


def mock_phone(country: str, seq: int, category_id: str) -> str:
    idx = _category_index(category_id)
    if country == "IN":
        return f"+91 80 00{idx % 100:02d} {seq:04d}"
    return f"+1 {_US_AREA_CODES[idx % len(_US_AREA_CODES)]} 555 01{seq % 100:02d}"


def _rng(*parts: object) -> random.Random:
    seed = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return random.Random(int(seed[:16], 16))  # noqa: S311 (not crypto)


def _pick_quality(rng: random.Random) -> Quality:
    total = sum(w for _, w in _QUALITY_WEIGHTS)
    roll = rng.uniform(0, total)
    for q, w in _QUALITY_WEIGHTS:
        roll -= w
        if roll <= 0:
            return q
    return "decent"


def businesses_for(
    city_id: str,
    city_name: str,
    state: str,
    country: str,
    lat: float,
    lng: float,
    category_id: str,
    count: int,
) -> list[MockBusiness]:
    parts = _NAME_PARTS.get(category_id, _DEFAULT_PARTS)
    out: list[MockBusiness] = []
    for i in range(1, count + 1):
        rng = _rng(city_id, category_id, i)
        quality = _pick_quality(rng)
        name = f"Sample {parts[i % len(parts)]} {i:02d} {city_name}"
        slug = site_slug(i, category_id, city_id, country)
        scheme = "https" if rng.random() < 0.6 else "http"
        website = None if quality == "none" else f"{scheme}://{slug}.example/"
        phone = mock_phone(country, i, category_id)
        out.append(
            MockBusiness(
                place_id=f"mock_{city_id}_{category_id}_{i:02d}",
                name=name,
                category=category_id,
                city=city_name,
                state=state,
                country=country,
                lat=round(lat + rng.uniform(-0.08, 0.08), 6),
                lng=round(lng + rng.uniform(-0.08, 0.08), 6),
                phone_international=phone,
                website=website,
                quality=quality,
                rating=round(rng.uniform(3.6, 4.9), 1),
                review_count=rng.randint(4, 900),
                seq=i,
            )
        )
    # One intentional duplicate listing (same business, second place_id) to exercise dedup.
    if out:
        first = out[0]
        out.append(
            MockBusiness(
                **{
                    **first.__dict__,
                    "place_id": first.place_id + "_dup",
                    "name": first.name + " (Branch Listing)",
                    "seq": first.seq,
                }
            )
        )
    return out


def places_payload(b: MockBusiness) -> dict[str, Any]:
    """Shape matches a Places API (New) Text Search `places[]` item for our field mask."""
    payload: dict[str, Any] = {
        "id": b.place_id,
        "displayName": {"text": b.name, "languageCode": "en"},
        "formattedAddress": f"{b.seq} Sample Street, {b.city}, {b.state}, {b.country}",
        "addressComponents": [
            {"longText": b.city, "types": ["locality"]},
            {"longText": b.state, "shortText": b.state, "types": ["administrative_area_level_1"]},
            {"longText": b.country, "shortText": b.country, "types": ["country"]},
        ],
        "location": {"latitude": b.lat, "longitude": b.lng},
        "internationalPhoneNumber": b.phone_international,
        "nationalPhoneNumber": b.phone_international.split(" ", 1)[1],
        "rating": b.rating,
        "userRatingCount": b.review_count,
        "businessStatus": "OPERATIONAL",
        "googleMapsUri": f"https://maps.google.com/?cid=mock-{b.place_id}",
        "regularOpeningHours": {
            "weekdayDescriptions": [
                "Monday: 9:00 AM – 7:00 PM",
                "Tuesday: 9:00 AM – 7:00 PM",
                "Wednesday: 9:00 AM – 7:00 PM",
                "Thursday: 9:00 AM – 7:00 PM",
                "Friday: 9:00 AM – 7:00 PM",
                "Saturday: 10:00 AM – 2:00 PM",
                "Sunday: Closed",
            ]
        },
    }
    if b.website:
        payload["websiteUri"] = b.website
    return payload


# ---------------------------------------------------------------------------
# Mock websites
# ---------------------------------------------------------------------------


def _business_from_domain(domain: str) -> tuple[str, Quality, str, random.Random]:
    """Recover (name, quality, phone, rng) from a slug made by site_slug()."""
    rng = _rng("site", domain)
    slug = domain.removesuffix(".example")
    try:
        head, category, city, cc = slug.split("--")
        seq = int(head.removeprefix("sample-"))
    except ValueError:
        return slug, "decent", "+1 512 555 0100", rng
    quality = _pick_quality(_rng(city, category, seq))
    name = f"Sample {category.replace('-', ' ').title()} {seq:02d}"
    return name, quality, mock_phone(cc.upper(), seq, category), rng


def mock_site_response(url: str) -> tuple[int, dict[str, str], str]:
    """Return (status, headers, body) for a GET on a mock `.example` site."""
    _scheme, rest = url.split("://", 1)
    domain, _, path = rest.partition("/")
    path = "/" + path.split("?", 1)[0]
    name, quality, phone, rng = _business_from_domain(domain)
    headers = {"content-type": "text/html; charset=utf-8"}
    if quality in ("good", "decent"):
        headers.update(
            {
                "strict-transport-security": "max-age=31536000",
                "x-content-type-options": "nosniff",
                "content-security-policy": "default-src 'self'",
            }
        )

    if path == "/robots.txt":
        body = "User-agent: *\nDisallow: /private/\n"
        if quality == "good":
            body += f"Sitemap: https://{domain}/sitemap.xml\n"
        if quality == "dated":
            body += "Crawl-delay: 2\n"
        return 200, {"content-type": "text/plain"}, body
    if path == "/sitemap.xml" and quality == "good":
        return (
            200,
            {"content-type": "application/xml"},
            ('<?xml version="1.0"?><urlset><url><loc>https://' + domain + "/</loc></url></urlset>"),
        )
    if quality == "parked":
        return (
            200,
            headers,
            (
                "<html><head><title>" + domain + " is for sale</title></head><body>"
                "<h1>This domain may be for sale</h1><p>Buy this domain. Parked free, courtesy of "
                "GoDaddy.com.</p></body></html>"
            ),
        )
    if quality == "challenge":
        return (
            403,
            {**headers, "server": "cloudflare", "cf-ray": "mock"},
            (
                "<html><head><title>Just a moment...</title></head><body>"
                "<div id='challenge-platform'>Checking your browser before accessing</div></body></html>"
            ),
        )

    pages = {"/", "/contact", "/contact/", "/about", "/about/", "/contact-us", "/about-us"}
    if path not in pages:
        return 404, headers, "<html><body><h1>Not found</h1></body></html>"
    return 200, headers, _render_site(domain, name, quality, phone, path, rng)


def _render_site(
    domain: str, name: str, quality: Quality, phone: str, path: str, rng: random.Random
) -> str:
    email_user = rng.choice(["info", "hello", "contact", "appointments"])
    email = f"{email_user}@{domain}"
    year = {"poor": 2014, "dated": 2019}.get(quality, 2026)
    nav = '<a href="/">Home</a> <a href="/about">About</a> <a href="/contact">Contact us</a>'

    if quality == "poor":
        # No viewport, table layout, obfuscated email, heavy inline images, no meta description.
        contact = (
            f"<p>Email: {email_user} [at] {domain.replace('.', ' [dot] ')}</p>"
            if path.startswith("/contact")
            else ""
        )
        return (
            f"<html><head><title>{name}</title>"
            '<script src="/js/jquery-1.8.3.min.js"></script></head>'
            f'<body bgcolor="#ffffcc"><table width="980"><tr><td>{nav}</td></tr>'
            f"<tr><td><font size=6>Welcome to {name}</font>"
            '<img src="/img/banner.jpg" width="980" height="400">'
            '<img src="/img/photo1.jpg"><img src="/img/photo2.jpg">'
            f"<p>Call {phone}</p>{contact}</td></tr>"
            f"<tr><td><small>Copyright {year} {name}. Best viewed in Internet Explorer.</small>"
            "</td></tr></table></body></html>"
        )

    viewport = '<meta name="viewport" content="width=device-width, initial-scale=1">'
    meta = (
        f'<meta name="description" content="{name} — trusted local service.">'
        if quality != "dated"
        else ""
    )
    og = (
        f'<meta property="og:title" content="{name}"><meta property="og:image" content="https://{domain}/og.jpg">'
        if quality == "good"
        else ""
    )
    canonical = f'<link rel="canonical" href="https://{domain}{path}">' if quality == "good" else ""
    jsonld = ""
    if quality in ("good", "decent"):
        jsonld = (
            '<script type="application/ld+json">{"@context":"https://schema.org",'
            f'"@type":"LocalBusiness","name":"{name}","telephone":"{phone}","email":"{email}",'
            '"address":{"@type":"PostalAddress","streetAddress":"1 Sample Street"}}</script>'
        )
    cta = (
        f'<a class="btn" href="tel:{phone.replace(" ", "")}">Call now</a> '
        f'<a href="https://wa.me/{phone.replace(" ", "").replace("+", "")}">WhatsApp</a>'
        if quality == "good"
        else '<a href="/contact">Get in touch</a>'
    )
    socials = (
        f'<a href="https://www.instagram.com/{domain.split(".")[0]}">Instagram</a> '
        f'<a href="https://www.facebook.com/{domain.split(".")[0]}">Facebook</a>'
    )
    builder = (
        '<meta name="generator" content="Wix.com Website Builder">' if quality == "dated" else ""
    )
    contact_block = ""
    if path.startswith("/contact"):
        contact_block = (
            f'<p>Write to us: <a href="mailto:{email}">{email}</a></p>'
            '<form><label>Name <input name="name"></label><button>Send</button></form>'
            + (
                '<iframe title="Map" src="https://www.google.com/maps?q=0,0&output=embed"></iframe>'
                if quality == "good"
                else ""
            )
        )
    hours = "<p>Hours: Mon–Fri 9am–7pm, Sat 10am–2pm</p>" if quality in ("good", "decent") else ""
    privacy = '<a href="/privacy">Privacy policy</a>' if quality in ("good", "decent") else ""
    return (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8">{viewport}'
        f"<title>{name} | Local experts</title>{meta}{og}{canonical}{builder}{jsonld}</head>"
        f"<body><header><nav>{nav}</nav></header><main><h1>{name}</h1>"
        f"<p>Serving the neighbourhood since 2009.</p>{cta}"
        '<img src="/img/hero.webp" alt="Our team at work" width="1200" height="600">'
        f"{hours}{contact_block}</main>"
        f"<footer><p>{name}, 1 Sample Street. Phone: {phone}</p>{socials} {privacy}"
        f"<p>&copy; {year} {name}</p></footer></body></html>"
    )
