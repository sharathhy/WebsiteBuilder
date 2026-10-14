"""The JSON site spec: the only thing the generator (and the LLM) produces for a site.

Templates in templates/site render a spec; nothing writes free-form code at runtime.
Fields the business has not published are left empty and listed in `placeholders`,
which the template renders as clearly marked placeholders. Never fabricate reviews,
awards, prices or staff.
"""

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

SPEC_VERSION = "1.1"

TemplateId = Literal[
    "restaurant",
    "clinic",
    "salon",
    "fitness",
    "legal-finance",
    "real-estate",
    "home-services",
    "generic-premium",
]
HeroModel = Literal["tooth", "plate", "droplet", "dumbbell", "pillar", "house", "wrench", "orb"]
SectionType = Literal[
    "services", "about", "social_proof", "gallery", "hours", "map", "faq", "pricing", "contact"
]

HEX = r"^#[0-9a-fA-F]{6}$"


class Address(BaseModel):
    street: str
    city: str
    state: str | None = None
    postal_code: str | None = None
    country: Literal["IN", "US"]


class HoursRow(BaseModel):
    day: Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    opens: str = Field(pattern=r"^\d{2}:\d{2}$")
    closes: str = Field(pattern=r"^\d{2}:\d{2}$")


class Social(BaseModel):
    platform: str
    url: HttpUrl


class BusinessInfo(BaseModel):
    name: str
    category: str
    tagline: str
    description: str
    phone_e164: str | None = None
    phone_display: str | None = None
    whatsapp_e164: str | None = None
    email: str | None = None
    address: Address
    lat: float | None = None
    lng: float | None = None
    google_maps_url: str | None = None
    hours: list[HoursRow] = Field(default_factory=list)
    # Real Google rating only; None when unknown.
    rating: float | None = Field(None, ge=0, le=5)
    review_count: int | None = Field(None, ge=0)
    socials: list[Social] = Field(default_factory=list)


class Seo(BaseModel):
    title: str = Field(max_length=70)
    description: str = Field(max_length=170)
    primary_keyword: str  # "{category} in {area}, {city}"
    keywords: list[str] = Field(default_factory=list)


class Theme(BaseModel):
    primary: str = Field(pattern=HEX)
    secondary: str = Field(pattern=HEX)
    accent: str = Field(pattern=HEX)
    background: str = Field(pattern=HEX)
    foreground: str = Field(pattern=HEX)
    mode: Literal["light", "dark"] = "light"
    font_heading: str = "Inter"
    font_body: str = "Inter"
    radius_px: int = Field(16, ge=0, le=40)


class Link(BaseModel):
    label: str
    href: str


class ImageAsset(BaseModel):
    src: str
    alt: str
    credit: str | None = None  # e.g. "Photo by X on Unsplash"
    credit_url: str | None = None


class VideoAsset(BaseModel):
    webm: str
    mp4: str
    poster: str


class Hero(BaseModel):
    headline: str
    subheadline: str
    cta_primary: Link
    cta_secondary: Link | None = None
    model: HeroModel = "orb"
    enable_3d: bool = True
    video: VideoAsset | None = None
    # Shown before the 3D scene loads and whenever WebGL or motion is unavailable.
    fallback_image: ImageAsset


class Service(BaseModel):
    title: str
    description: str
    icon: str = "sparkles"  # lucide icon name
    price: str | None = None  # only if the business publishes it


class About(BaseModel):
    heading: str
    body: str


class Testimonial(BaseModel):
    """Only real, attributable reviews the business has permission to show."""

    quote: str
    author: str
    source: str
    source_url: str | None = None


class SocialProof(BaseModel):
    rating: float | None = None
    review_count: int | None = None
    source: str = "Google"
    source_url: str | None = None
    testimonials: list[Testimonial] = Field(default_factory=list)


class Faq(BaseModel):
    q: str
    a: str


class PricingTier(BaseModel):
    name: str
    price: str
    features: list[str]


class Contact(BaseModel):
    form_endpoint: str  # LeadForge API: /api/public/forms/{site_id}
    site_id: str
    turnstile_site_key: str | None = None
    booking_url: str | None = None


class Analytics(BaseModel):
    enabled: bool = False
    provider: Literal["plausible", "ga4"] | None = None
    id: str | None = None


PageKind = Literal[
    "about", "services", "services-detail", "menu", "pricing", "team", "gallery",
    "testimonials", "faq", "blog", "blog-detail", "booking", "contact", "location", "events",
    "careers", "terms", "other",
]  # fmt: skip


class Page(BaseModel):
    """An inner page that mirrors a page of the business's current site (page parity).

    Copy is written from the business facts LeadForge holds, never copied from the old
    page; whatever only the owner can supply is listed in `placeholders` and rendered on
    the page as a clearly marked placeholder."""

    path: str = Field(pattern=r"^/[a-z0-9-]+(?:/[a-z0-9-]+)*$")  # no trailing slash
    kind: PageKind
    nav_label: str = Field(max_length=40)
    in_nav: bool = True
    parent: str | None = None  # path of the parent page, for nested pages
    title: str = Field(max_length=70)
    description: str = Field(max_length=170)
    heading: str
    intro: str
    sections: list[SectionType] = Field(default_factory=list)
    placeholders: list[str] = Field(default_factory=list)
    source_path: str | None = None  # the page's path on the current site


class Redirect(BaseModel):
    """An old address that must keep working, e.g. /menu.html -> /menu."""

    from_path: str = Field(pattern=r"^/[A-Za-z0-9._~!$&'()*+,;=:@%/-]*$")
    to_path: str


class SiteSpec(BaseModel):
    spec_version: str = SPEC_VERSION
    template: TemplateId
    locale: Literal["en-IN", "en-US"]
    currency: Literal["INR", "USD"]
    site_url: str
    noindex: bool = True
    business: BusinessInfo
    seo: Seo
    theme: Theme
    hero: Hero
    sections: list[SectionType]
    services: list[Service] = Field(default_factory=list)
    about: About | None = None
    social_proof: SocialProof = SocialProof()
    gallery: list[ImageAsset] = Field(default_factory=list)
    faq: list[Faq] = Field(default_factory=list)
    pricing: list[PricingTier] = Field(default_factory=list)
    contact: Contact
    analytics: Analytics = Analytics()
    # Inner pages, one per page of the current site (the home page is the spec itself).
    pages: list[Page] = Field(default_factory=list)
    redirects: list[Redirect] = Field(default_factory=list)
    # Human-readable list of things the owner must supply, e.g. "Team photos".
    placeholders: list[str] = Field(default_factory=list)
    attribution: list[str] = Field(default_factory=list)
