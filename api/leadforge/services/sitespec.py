"""Build the JSON site spec for a business. The LLM only fills copy; all facts come
from stored data, and anything unknown becomes a visible placeholder."""

import hashlib
import json
import re
from typing import Any

from pydantic import BaseModel, Field

from leadforge.models import Business
from leadforge.schemas.site_spec import (
    About,
    Address,
    Analytics,
    BusinessInfo,
    Contact,
    Faq,
    Hero,
    HoursRow,
    ImageAsset,
    Link,
    Seo,
    Service,
    SiteSpec,
    Social,
    SocialProof,
    Theme,
)
from leadforge.services import pages as page_plan
from leadforge.services.contacts import national_format

TEMPLATE_MODEL = {
    "clinic": "tooth", "restaurant": "plate", "salon": "droplet", "fitness": "dumbbell",
    "legal-finance": "pillar", "real-estate": "house", "home-services": "wrench",
    "generic-premium": "orb",
}  # fmt: skip
ICONS = {
    "clinic": ["stethoscope", "smile", "shield-check", "calendar", "sparkles", "heart-pulse"],
    "restaurant": ["utensils", "chef-hat", "wine", "truck", "calendar", "cake"],
    "salon": ["scissors", "sparkles", "flower", "palette", "gem", "heart"],
}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class SiteCopy(BaseModel):
    tagline: str = Field(max_length=90)
    description: str
    hero_headline: str = Field(max_length=80)
    hero_subheadline: str = Field(max_length=200)
    services: list[Service] = Field(min_length=3, max_length=6)
    about_heading: str
    about_body: str
    faq: list[Faq] = Field(max_length=6)
    seo_title: str = Field(max_length=70)
    seo_description: str = Field(max_length=170)
    placeholders: list[str] = Field(default_factory=list)


_SERVICE_DEFAULTS: dict[str, list[tuple[str, str]]] = {
    "clinic": [
        (
            "Check-ups & cleaning",
            "Routine examinations and professional cleaning to keep problems small.",
        ),
        (
            "Fillings & restorations",
            "Repair decayed or damaged teeth so they look and work naturally.",
        ),
        ("Root canal treatment", "Relieve pain and save an infected tooth instead of removing it."),
        ("Cosmetic dentistry", "Whitening, veneers and smile makeovers, planned around you."),
        (
            "Emergency appointments",
            "Toothache or a broken tooth? Call and we'll fit you in as soon as we can.",
        ),
    ],
    "restaurant": [
        ("Dine-in", "A relaxed table for lunch or dinner with friends and family."),
        ("Takeaway & delivery", "Order ahead and pick up, or get it delivered to your door."),
        ("Private events", "Birthdays, team dinners and celebrations, tailored to your group."),
        ("Catering", "Food for your office or home event, planned with you."),
    ],
    "salon": [
        ("Haircuts & styling", "Cuts, blow-dries and styling for every hair type."),
        ("Colour", "Highlights, balayage and full colour, matched to you."),
        ("Skin & facials", "Treatments that leave your skin calm, clean and glowing."),
        ("Bridal & occasion", "Hair and make-up for your big day and the days around it."),
        ("Spa treatments", "Massages and relaxation treatments to unwind."),
    ],
}
_GENERIC_SERVICES = [
    ("Consultations", "Talk to us about what you need and get clear advice."),
    ("Core services", "The work we're known for, done carefully and on time."),
    ("Ongoing support", "We stay available after the job is done."),
    ("Custom requests", "Tell us what you need and we'll tell you honestly if we can help."),
]


def _area(biz: Business) -> str:
    parts = [p.strip() for p in (biz.address or "").split(",")]
    for p in parts[1:-2]:
        if p and p != biz.city and not re.search(r"\d", p):
            return p
    return biz.city


def mock_copy(biz: Business, category_label: str, template: str, locale: str) -> SiteCopy:
    """Deterministic copy used in MOCK_APIS mode; same content rules as the prompt."""
    area = _area(biz)
    place = area if area.lower() == biz.city.lower() else f"{area}, {biz.city}"
    services = [
        Service(title=t, description=d, icon=(ICONS.get(template) or ["sparkles"] * 6)[i % 6])
        for i, (t, d) in enumerate(_SERVICE_DEFAULTS.get(template, _GENERIC_SERVICES))
    ]
    noun = (
        category_label.lower().rstrip("s")
        if category_label.endswith("s")
        else category_label.lower()
    )
    return SiteCopy(
        tagline=f"Trusted {noun} care in {area}"[:90],
        description=(
            f"{biz.name} is a {noun} in {place}. Call or message us to ask a question "
            "or book a visit."
        ),
        hero_headline=f"{category_label.rstrip('s')} in {place}"[:80],
        hero_subheadline=(
            f"{biz.name}: easy to reach, simple to book, and happy to answer your questions."
        )[:200],
        services=services[:6],
        about_heading=f"About {biz.name}",
        about_body=(
            f"We're a local {noun} serving {area} and the rest of {biz.city}. "
            "This section will tell our story in our own words once we've shared it."
        ),
        faq=[
            Faq(
                q="How do I book?",
                a="Call us or send a WhatsApp message and we'll find a time that works.",
            ),
            Faq(
                q="Where are you located?",
                a=f"We're at {biz.address}. The map below has directions.",
            ),
            Faq(
                q="What are your opening hours?",
                a="Our current hours are listed on this page. Call ahead on public holidays.",
            ),
            Faq(
                q="How much does it cost?",
                a="It depends on what you need. Call us and we'll explain the options.",
            ),
        ],
        seo_title=f"{biz.name} | {category_label} in {area}"[:60],
        seo_description=(
            f"{biz.name}: {noun} in {place}. See services, hours and location, "
            "then call or message to book."
        )[:155],
        placeholders=[
            "Team photos and introductions",
            "Our story (about section)",
            "Service prices (if you'd like to publish them)",
        ],
    )


def parse_hours(hours: dict[str, Any] | None) -> list[HoursRow]:
    """Places regularOpeningHours.weekdayDescriptions -> structured rows (24h)."""
    rows: list[HoursRow] = []
    for line in (hours or {}).get("weekdayDescriptions", []):
        m = re.match(
            r"(\w+):\s*(\d{1,2}):(\d{2})\s*([AP]M)\s*[–-]\s*(\d{1,2}):(\d{2})\s*([AP]M)", line
        )
        if not m or m.group(1) not in DAYS:
            continue

        def to24(h: str, mi: str, ap: str) -> str:
            hh = int(h) % 12 + (12 if ap == "PM" else 0)
            return f"{hh:02d}:{mi}"

        rows.append(
            HoursRow(
                day=m.group(1),
                opens=to24(*m.group(2, 3, 4)),
                closes=to24(*m.group(5, 6, 7)),
            )
        )
    return rows


def site_slug(biz: Business) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", biz.name.lower()).strip("-")[:32].strip("-")
    short = hashlib.sha1(str(biz.id).encode()).hexdigest()[:6]  # noqa: S324
    return f"{base}-{short}"


def facts_for(biz: Business) -> dict[str, Any]:
    return {
        "name": biz.name, "category": biz.category, "address": biz.address, "city": biz.city,
        "country": biz.country, "phone": biz.phone_e164, "google_rating": biz.rating,
        "google_review_count": biz.review_count, "hours": (biz.hours or {}).get("weekdayDescriptions"),
    }  # fmt: skip


def build_spec(
    *,
    biz: Business,
    copy: SiteCopy,
    template: str,
    palette: dict[str, str],
    site_url: str,
    site_id: str,
    form_endpoint: str,
    whatsapp: str | None,
    email: str | None,
    socials: list[str],
    hero_image: ImageAsset,
    gallery: list[ImageAsset],
    booking_url: str | None,
    turnstile_site_key: str | None,
    enable_3d: bool = True,
    inventory: list[dict[str, Any]] | None = None,
    category_label: str | None = None,
) -> SiteSpec:
    locale = "en-IN" if biz.country == "IN" else "en-US"
    phone_display = national_format(biz.phone_e164) if biz.phone_e164 else None
    area = _area(biz)
    place = area if area.lower() == biz.city.lower() else f"{area}, {biz.city}"
    hours = parse_hours(biz.hours)
    sections = ["services", "about", "social_proof"]
    if gallery:
        sections.append("gallery")
    if hours:
        sections.append("hours")
    if biz.lat is not None:
        sections.append("map")
    sections += ["faq", "contact"]
    placeholders = list(copy.placeholders)
    if not gallery:
        placeholders.append("Photos of your space (we don't use your photos without permission)")
    label = category_label or biz.category.replace("-", " ").title()
    noun = label.lower().rstrip("s") if label.endswith("s") else label.lower()
    inner, redirects = page_plan.plan_pages(
        inventory or [],
        name=biz.name,
        noun=noun,
        place=place,
        available=sections,  # type: ignore[arg-type]
        has_booking=bool(booking_url),
    )
    if any(p.placeholders for p in inner):
        n = sum(1 for p in inner if p.placeholders)
        placeholders.append(
            f"Content for {n} inner {'page' if n == 1 else 'pages'} (marked on each page)"
        )
    cta = (
        Link(label="Call now", href=f"tel:{biz.phone_e164}")
        if biz.phone_e164
        else Link(label="Send a message", href="#contact")
    )
    return SiteSpec(
        template=template,
        locale=locale,
        currency="INR" if biz.country == "IN" else "USD",
        site_url=site_url,
        noindex=True,
        business=BusinessInfo(
            name=biz.name,
            category=biz.category,
            tagline=copy.tagline,
            description=copy.description,
            phone_e164=biz.phone_e164,
            phone_display=phone_display,
            whatsapp_e164=whatsapp,
            email=email,
            address=Address(
                street=biz.address.split(",")[0],
                city=biz.city,
                state=biz.state,
                country=biz.country,
            ),
            lat=biz.lat,
            lng=biz.lng,
            google_maps_url=biz.google_maps_url,
            hours=hours,
            rating=biz.rating,
            review_count=biz.review_count,
            socials=[Social(platform=s.split("/")[2].split(".")[0], url=s) for s in socials][:5],
        ),
        seo=Seo(
            title=copy.seo_title,
            description=copy.seo_description,
            primary_keyword=f"{biz.category.replace('-', ' ')} in {place}",
            keywords=[biz.category.replace("-", " "), area, biz.city],
        ),
        theme=Theme(
            primary=palette["primary"],
            secondary=palette["secondary"],
            accent=palette["accent"],
            background=palette["background"],
            foreground=palette["foreground"],
        ),
        hero=Hero(
            headline=copy.hero_headline,
            subheadline=copy.hero_subheadline,
            cta_primary=cta,
            cta_secondary=Link(label="WhatsApp us", href=f"https://wa.me/{whatsapp.lstrip('+')}")
            if whatsapp
            else Link(label="Get directions", href=biz.google_maps_url or "#map"),
            model=TEMPLATE_MODEL.get(template, "orb"),
            enable_3d=enable_3d,
            fallback_image=hero_image,
        ),
        sections=sections,
        services=copy.services,
        about=About(heading=copy.about_heading, body=copy.about_body),
        social_proof=SocialProof(
            rating=biz.rating,
            review_count=biz.review_count,
            source="Google",
            source_url=biz.google_maps_url,
            testimonials=[],
        ),
        gallery=gallery,
        faq=copy.faq,
        contact=Contact(
            form_endpoint=form_endpoint,
            site_id=site_id,
            turnstile_site_key=turnstile_site_key,
            booking_url=booking_url,
        ),
        analytics=Analytics(enabled=False),
        pages=inner,
        redirects=redirects,
        placeholders=placeholders,
        attribution=[img.credit for img in [hero_image, *gallery] if img.credit],
    )


def spec_json(spec: SiteSpec) -> str:
    return json.dumps(spec.model_dump(mode="json"), indent=2, ensure_ascii=False)
