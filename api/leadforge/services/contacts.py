"""Contact extraction and validation: emails, phones, WhatsApp and social links.

Only publicly published contact points are kept, each with the URL it was found on.
Emails are never guessed or generated.
"""

import json
import re
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from urllib.parse import unquote, urljoin, urlsplit

import phonenumbers
from bs4 import BeautifulSoup

from leadforge.models.enums import ContactKind, ContactSource

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}")
OBFUSCATED_RE = re.compile(
    r"([A-Za-z0-9._%+-]+)\s*(?:\[\s*at\s*\]|\(\s*at\s*\)|\{\s*at\s*\}|\s+at\s+)\s*"
    r"([A-Za-z0-9-]+(?:\s*(?:\[\s*dot\s*\]|\(\s*dot\s*\)|\{\s*dot\s*\}|\s+dot\s+|\.)\s*[A-Za-z0-9-]+)+)",
    re.IGNORECASE,
)
DOT_RE = re.compile(r"\s*(?:\[\s*dot\s*\]|\(\s*dot\s*\)|\{\s*dot\s*\}|\s+dot\s+)\s*", re.I)

ROLE_LOCALPARTS = {
    "info", "contact", "hello", "hi", "admin", "office", "sales", "support", "enquiry",
    "enquiries", "inquiries", "reception", "appointments", "booking", "bookings", "team",
    "care", "frontdesk", "mail", "help",
}  # fmt: skip
FREE_PROVIDERS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "rediffmail.com",
    "yahoo.co.in", "aol.com", "proton.me", "protonmail.com", "zoho.com",
}  # fmt: skip
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com", "yopmail.com",
    "trashmail.com", "getnada.com", "dispostable.com", "sharklasers.com", "maildrop.cc",
    "temp-mail.org", "throwawaymail.com", "fakeinbox.com",
}  # fmt: skip
BAD_EMAIL_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js")
PLACEHOLDER_EMAILS = {"you@example.com", "email@example.com", "name@domain.com", "user@domain.com"}

SOCIAL_HOSTS = {
    "facebook.com": "facebook",
    "instagram.com": "instagram",
    "linkedin.com": "linkedin",
    "twitter.com": "x",
    "x.com": "x",
    "youtube.com": "youtube",
    "tiktok.com": "tiktok",
    "pinterest.com": "pinterest",
}


@dataclass
class FoundContact:
    kind: ContactKind
    value: str
    source: ContactSource
    source_url: str
    label: str | None = None
    confidence: float = 0.0
    is_role_address: bool | None = None
    mx_valid: bool | None = None
    is_disposable: bool | None = None


def _clean_email(raw: str) -> str | None:
    email = unquote(raw).strip().strip(".,;:").lower()
    email = email.split("?", 1)[0]
    if not EMAIL_RE.fullmatch(email):
        return None
    if email.endswith(BAD_EMAIL_SUFFIXES) or email in PLACEHOLDER_EMAILS:
        return None
    local, _, domain = email.partition("@")
    if not local or ".." in email or domain.startswith("-"):
        return None
    return email


def extract_emails(html: str, page_url: str) -> list[FoundContact]:
    soup = BeautifulSoup(html, "lxml")
    found: dict[str, FoundContact] = {}

    def add(email: str | None, source: ContactSource) -> None:
        if email and email not in found:
            found[email] = FoundContact(ContactKind.EMAIL, email, source, page_url)

    for a in soup.select('a[href^="mailto:" i]'):
        add(_clean_email(str(a.get("href", ""))[7:]), ContactSource.MAILTO)
    for node in _jsonld_nodes(soup):
        email = node.get("email")
        if isinstance(email, str):
            add(_clean_email(email.removeprefix("mailto:")), ContactSource.JSON_LD)
    text = soup.get_text(" ", strip=True)
    for match in EMAIL_RE.findall(text):
        add(_clean_email(match), ContactSource.PAGE_TEXT)
    for local, domain in OBFUSCATED_RE.findall(text):
        add(
            _clean_email(f"{local}@{DOT_RE.sub('.', domain).replace(' ', '')}"),
            ContactSource.PAGE_TEXT,
        )
    return list(found.values())


def extract_phones(html: str, page_url: str, region: str) -> list[FoundContact]:
    soup = BeautifulSoup(html, "lxml")
    found: dict[str, FoundContact] = {}

    def add(raw: str, source: ContactSource) -> None:
        e164 = normalize_phone(raw, region)
        if e164 and e164 not in found:
            found[e164] = FoundContact(ContactKind.PHONE, e164, source, page_url)

    for a in soup.select('a[href^="tel:" i]'):
        add(str(a.get("href", ""))[4:], ContactSource.PAGE_TEXT)
    for node in _jsonld_nodes(soup):
        tel = node.get("telephone")
        if isinstance(tel, str):
            add(tel, ContactSource.JSON_LD)
    text = soup.get_text(" ", strip=True)
    for m in phonenumbers.PhoneNumberMatcher(text, region):
        add(
            phonenumbers.format_number(m.number, phonenumbers.PhoneNumberFormat.E164),
            ContactSource.PAGE_TEXT,
        )
    return list(found.values())


def extract_links(html: str, page_url: str) -> list[FoundContact]:
    """WhatsApp and social profile links."""
    soup = BeautifulSoup(html, "lxml")
    out: dict[str, FoundContact] = {}
    for a in soup.select("a[href]"):
        href = urljoin(page_url, str(a.get("href", "")))
        parts = urlsplit(href)
        host = parts.netloc.lower().removeprefix("www.").removeprefix("m.")
        if host in ("wa.me", "api.whatsapp.com", "web.whatsapp.com"):
            digits = re.sub(r"\D", "", parts.path) or re.sub(
                r"\D",
                "",
                dict(p.split("=", 1) for p in parts.query.split("&") if "=" in p).get("phone", ""),
            )
            if digits:
                value = f"+{digits}"
                out.setdefault(
                    "wa" + value,
                    FoundContact(
                        ContactKind.WHATSAPP,
                        value,
                        ContactSource.PAGE_TEXT,
                        page_url,
                        label="whatsapp",
                        confidence=0.9,
                    ),
                )
        elif host in SOCIAL_HOSTS and parts.path.strip("/"):
            canonical = f"https://{host}{parts.path.rstrip('/')}"
            out.setdefault(
                canonical,
                FoundContact(
                    ContactKind.SOCIAL,
                    canonical,
                    ContactSource.PAGE_TEXT,
                    page_url,
                    label=SOCIAL_HOSTS[host],
                    confidence=0.8,
                ),
            )
    return list(out.values())


def candidate_pages(html: str, base_url: str) -> list[str]:
    """Same-site links likely to hold contact details, in priority order."""
    soup = BeautifulSoup(html, "lxml")
    base_host = urlsplit(base_url).netloc.lower()
    keywords = ("contact", "about", "reach", "location", "find-us", "visit", "team", "imprint")
    scored: list[tuple[int, str]] = []
    for a in soup.select("a[href]"):
        href = urljoin(base_url, str(a.get("href", ""))).split("#", 1)[0]
        parts = urlsplit(href)
        if parts.scheme not in ("http", "https") or parts.netloc.lower() != base_host:
            continue
        hay = (parts.path + " " + a.get_text(" ", strip=True)).lower()
        for rank, kw in enumerate(keywords):
            if kw in hay:
                scored.append((rank, href))
                break
    seen: set[str] = set()
    ordered = []
    for _, href in sorted(scored):
        if href not in seen:
            seen.add(href)
            ordered.append(href)
    for guess in ("/contact", "/contact-us", "/about", "/about-us"):
        url = urljoin(base_url, guess)
        if url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered


def normalize_phone(raw: str, region: str) -> str | None:
    try:
        num = phonenumbers.parse(raw, region)
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_possible_number(num):
        return None
    return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)


def national_format(e164: str) -> str:
    try:
        num = phonenumbers.parse(e164, None)
    except phonenumbers.NumberParseException:
        return e164
    return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.NATIONAL)


MxResolver = Callable[[str], Awaitable[bool]]


async def validate_email(
    contact: FoundContact, site_domain: str | None, mx_resolver: MxResolver
) -> FoundContact:
    """Fill confidence, role, disposable and MX flags. Confidence is 0..1."""
    local, _, domain = contact.value.partition("@")
    contact.is_role_address = local in ROLE_LOCALPARTS
    contact.is_disposable = domain in DISPOSABLE_DOMAINS
    contact.mx_valid = await mx_resolver(domain)
    site_root = (site_domain or "").removeprefix("www.")
    if contact.is_disposable or not contact.mx_valid:
        confidence = 0.1
    elif site_root and (domain == site_root or domain.endswith("." + site_root)):
        confidence = 0.95
    elif domain in FREE_PROVIDERS:
        confidence = 0.7
    else:
        confidence = 0.5
    if contact.source == ContactSource.PAGE_TEXT and confidence > 0.5:
        confidence -= 0.05
    contact.confidence = round(confidence, 2)
    contact.label = f"{local}@" if contact.is_role_address else None
    return contact


def best_email(contacts: Iterable[FoundContact]) -> FoundContact | None:
    emails = [c for c in contacts if c.kind == ContactKind.EMAIL and not c.is_disposable]
    return max(emails, key=lambda c: c.confidence, default=None)


def _jsonld_nodes(soup: BeautifulSoup) -> list[dict[str, object]]:
    nodes: list[dict[str, object]] = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        stack = [data]
        while stack:
            item = stack.pop()
            if isinstance(item, list):
                stack.extend(item)
            elif isinstance(item, dict):
                nodes.append(item)
                graph = item.get("@graph")
                if isinstance(graph, list):
                    stack.extend(graph)
    return nodes


def jsonld_types(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    types: list[str] = []
    for node in _jsonld_nodes(soup):
        t = node.get("@type")
        if isinstance(t, str):
            types.append(t)
        elif isinstance(t, list):
            types.extend(str(x) for x in t)
    return types
