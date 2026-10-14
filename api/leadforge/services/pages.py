"""Page parity: list every page of a business's current site and plan the same pages on the
replacement site.

The inventory records structure only (path, nav label, page title, a page kind). Page
bodies are never stored or copied: each new page is written from the business facts we
already hold, and anything only the owner can supply (menus, bios, prices, blog posts)
becomes a clearly marked placeholder.
"""

import re
from dataclasses import asdict, dataclass
from typing import Any, Protocol
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup

from leadforge.clients.web import FetchResult
from leadforge.schemas.site_spec import Page, Redirect, SectionType

# Paths that are not content pages: assets, feeds, admin and account areas, carts.
_SKIP_EXT = re.compile(
    r"\.(?:jpe?g|png|gif|webp|avif|svg|ico|pdf|docx?|xlsx?|pptx?|zip|rar|mp[34]|mov|webm|"
    r"css|js|json|xml|txt|rss|atom|woff2?|ttf|eot)$",
    re.I,
)
_SKIP_PATH = re.compile(
    r"^/(?:wp-admin|wp-login|wp-json|wp-content|wp-includes|admin|login|logout|signin|"
    r"sign-in|register|account|my-account|cart|checkout|basket|feed|cdn-cgi|"
    r"search|tag|tags|author|category/page)(?:/|$)",
    re.I,
)
# Old sites often serve /about.html or /about.php; the new site gets a clean /about/ page
# and keeps the old address working.
_LEGACY_EXT = re.compile(r"\.(?:html?|php|aspx?|jsp|cfm)$", re.I)
_INDEX = re.compile(r"/(?:index|default|home)\.(?:html?|php|aspx?|jsp)$", re.I)

# (kind, keywords matched against the path and the nav label), first match wins.
_KINDS: list[tuple[str, tuple[str, ...]]] = [
    ("privacy", ("privacy", "cookie")),
    ("terms", ("terms", "conditions", "legal", "disclaimer", "imprint")),
    ("contact", ("contact", "reach-us", "get-in-touch", "enquir", "inquir")),
    ("booking", ("book", "appointment", "reserv", "schedule")),
    ("menu", ("menu", "food", "drinks", "wine-list")),
    ("pricing", ("pric", "rates", "fees", "tariff", "membership", "packages")),
    ("team", ("team", "staff", "doctor", "dentist", "stylist", "people", "our-experts")),
    ("gallery", ("gallery", "photo", "portfolio", "lookbook", "before-after", "our-work")),
    ("testimonials", ("testimonial", "review", "patient-stories", "what-clients-say")),
    ("faq", ("faq", "question", "help")),
    ("blog", ("blog", "news", "article", "insight", "updates", "press")),
    ("careers", ("career", "jobs", "join-us", "hiring", "vacanc")),
    ("events", ("event", "private-dining", "catering", "party", "parties")),
    ("location", ("location", "find-us", "directions", "areas", "visit-us", "branches")),
    ("services", ("service", "treatment", "what-we-do", "practice-area", "offerings")),
    ("about", ("about", "our-story", "who-we-are", "history", "mission")),
]


@dataclass
class PageInfo:
    path: str  # normalized original path, e.g. "/services/teeth-whitening" or "/menu.html"
    label: str  # nav/link text, else the page <h1>/<title>
    kind: str
    title: str | None = None  # the original <title>, for reference only
    source: str = "link"  # "home", "link" or "sitemap"
    status: int | None = None
    fetched: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class Fetcher(Protocol):
    async def get(self, url: str, *, check_robots: bool = True) -> FetchResult: ...

    async def allowed(self, url: str) -> bool: ...


def normalize_path(url: str, base_url: str) -> str | None:
    """Same-site content-page path for a link, or None to ignore it."""
    absolute = urljoin(base_url, url.strip())
    parts = urlsplit(absolute)
    base = urlsplit(base_url)
    if parts.scheme not in ("http", "https"):
        return None
    if parts.netloc.lower().removeprefix("www.") != base.netloc.lower().removeprefix("www."):
        return None
    path = unquote(parts.path or "/")
    path = re.sub(r"/{2,}", "/", path)
    if _INDEX.search(path):
        path = path[: path.rfind("/") + 1]
    if path != "/":
        path = path.rstrip("/") or "/"
    path = path.lower()
    if _SKIP_EXT.search(path) or _SKIP_PATH.search(path):
        return None
    if path.count("/") > 3:  # deep archive pages; the cap keeps the inventory to real pages
        return None
    return path


def classify(path: str, label: str = "") -> str:
    if path == "/":
        return "home"
    depth = path.strip("/").count("/")
    # The path is the stronger signal ("/gallery" titled "Lookbook" is a gallery), so try it
    # before the label.
    for hay in (path.lower(), label.lower().replace(" ", "-")):
        for kind, keys in _KINDS:
            if any(k in hay for k in keys):
                if depth >= 1 and kind in ("services", "blog"):
                    return f"{kind}-detail"
                return kind
    return "other"


def humanize(path: str) -> str:
    leaf = _LEGACY_EXT.sub("", path.rstrip("/").rsplit("/", 1)[-1]) or "Home"
    words = re.sub(r"[-_]+", " ", leaf).strip()
    return words[:1].upper() + words[1:]


def page_links(html: str, base_url: str) -> list[tuple[str, str]]:
    """(path, link text) for same-site page links, nav and header links first."""
    soup = BeautifulSoup(html, "lxml")
    anchors = soup.select("nav a[href], header a[href]") + soup.select("a[href]")
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for a in anchors:
        path = normalize_path(str(a.get("href", "")), base_url)
        if path is None or path in seen:
            continue
        seen.add(path)
        text = a.get_text(" ", strip=True) or str(a.get("title") or a.get("aria-label") or "")
        out.append((path, text[:80]))
    return out


def sitemap_paths(xml: str, base_url: str) -> list[str]:
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml, re.I)
    paths = []
    for loc in locs:
        path = normalize_path(loc, base_url)
        if path is not None and path not in paths:
            paths.append(path)
    return paths


def _page_title(html: str) -> tuple[str | None, str | None]:
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    h1 = soup.find("h1")
    return title, (h1.get_text(" ", strip=True) if h1 else None)


async def build_inventory(
    fetcher: Fetcher,
    home: FetchResult,
    *,
    max_pages: int = 30,
    fetched: dict[str, FetchResult] | None = None,
) -> tuple[list[PageInfo], dict[str, Any]]:
    """Every public page of the current site: links on the home page, the pages they link
    to, and the sitemap. Each page is fetched through the polite fetcher (robots.txt,
    crawl-delay, per-domain rate limit) to confirm it exists; 404s and pages robots.txt
    disallows are left out. Returns (pages, stats)."""
    base = home.final_url
    root = urljoin(base, "/")
    fetched = dict(fetched or {})
    pages: dict[str, PageInfo] = {
        "/": PageInfo("/", "Home", "home", _page_title(home.text)[0], "home", home.status, True)
    }
    labels: dict[str, str] = {}
    sources: dict[str, str] = {}
    queue: list[str] = []

    def push(path: str, label: str, source: str) -> None:
        if path not in labels or (not labels[path] and label):
            labels[path] = label
        if path not in sources:
            sources[path] = source
            queue.append(path)

    for path, text in page_links(home.text, base):
        push(path, text, "link")

    sitemap_count = 0
    sitemap_urls = [urljoin(root, "sitemap.xml")]
    robots = await fetcher.get(urljoin(root, "robots.txt"), check_robots=False)
    if robots.ok:
        sitemap_urls = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots.text) or sitemap_urls
    for sm_url in sitemap_urls[:3]:
        sm = await fetcher.get(sm_url)
        if sm.ok and "<urlset" in sm.text.lower():
            for path in sitemap_paths(sm.text, base):
                sitemap_count += 1
                push(path, "", "sitemap")

    skipped_robots = missing = 0
    i = 0
    while i < len(queue) and len(pages) < max_pages:
        path = queue[i]
        i += 1
        if path == "/":
            continue
        url = urljoin(root, path.lstrip("/"))
        res = fetched.get(url) or fetched.get(url + "/")
        if res is None:
            if not await fetcher.allowed(url):
                skipped_robots += 1
                continue
            res = await fetcher.get(url)
        if res.error == "blocked_by_robots":
            skipped_robots += 1
            continue
        ctype = res.headers.get("content-type", "text/html")
        if not res.ok or "html" not in ctype:
            missing += 1
            continue
        title, h1 = _page_title(res.text)
        label = labels.get(path) or h1 or humanize(path)
        pages[path] = PageInfo(
            path, label, classify(path, label), title, sources[path], res.status, True
        )
        # One level of discovery from each page (e.g. /services -> /services/implants).
        for sub, text in page_links(res.text, res.final_url):
            push(sub, text, "link")

    stats = {
        "discovered": len(sources) + 1,
        "in_sitemap": sitemap_count,
        "skipped_robots": skipped_robots,
        "not_found": missing,
        "truncated": len(queue) - i > 0 and len(pages) >= max_pages,
    }
    # Home first, then discovery order (nav order) within each depth.
    ordered = sorted(pages.values(), key=lambda p: (p.path != "/", p.path.count("/")))
    return ordered, stats


def clean_path(path: str) -> str:
    """Where a page lives on the new site: lowercase, hyphenated, no legacy extension."""
    if path == "/":
        return "/"
    segs = []
    for seg in _LEGACY_EXT.sub("", path).strip("/").split("/"):
        seg = re.sub(r"[^a-z0-9]+", "-", seg.lower()).strip("-")
        if seg:
            segs.append(seg)
    return "/" + "/".join(segs) if segs else "/"


# Paths the template already renders itself.
BUILTIN_PATHS = {"/", "/privacy"}


# ---------------------------------------------------------------------------
# Planning the new site's pages
# ---------------------------------------------------------------------------

# kind -> (sections to show, placeholders the owner must supply). "{label}" and "{name}"
# are filled in per page. Sections the business has no data for are dropped later.
_PLAN: dict[str, tuple[list[SectionType], list[str]]] = {
    "about": (["about", "social_proof", "contact"],
              ["Your story, in your own words", "Team photos and introductions"]),
    "services": (["services", "faq", "contact"], []),
    "services-detail": (["contact"], [
        "What {label} involves, how long it takes and what it costs (from {name})"]),
    "menu": (["hours", "contact"], [
        "Menu items and prices (send us your current menu; we don't copy it from the old site)"]),
    "pricing": (["services", "contact"], ["Prices, only if you choose to publish them"]),
    "team": (["about", "contact"],
             ["Team names, photos and short bios (with each person's consent)"]),
    "gallery": (["gallery", "contact"],
                ["Photos of your space and work (we don't use your photos without permission)"]),
    "testimonials": (["social_proof", "contact"],
                     ["Customer testimonials you have permission to show"]),
    "faq": (["faq", "contact"], []),
    "blog": (["contact"], ["Your blog posts, moved over with your permission"]),
    "blog-detail": (["contact"], ["The article “{label}”, moved over with your permission"]),
    "booking": (["contact", "hours"], ["Your online booking link, if you use a booking system"]),
    "contact": (["contact", "hours", "map"], []),
    "location": (["map", "hours", "contact"], ["Areas you serve or other branches"]),
    "events": (["contact"], ["Event packages, capacity and how to enquire"]),
    "careers": (["contact"], ["Open roles and how to apply"]),
    "terms": ([], ["Terms of service text (from you or your lawyer)"]),
    "other": (["contact"], ["Content for “{label}” (from {name})"]),
}  # fmt: skip

_INTRO: dict[str, str] = {
    "about": "{name} is a {noun} in {place}.",
    "services": "What {name} offers in {place}. Call or message to ask which option suits you.",
    "services-detail": "{label} at {name} in {place}. Get in touch to ask whether it's right "
    "for you and to book.",
    "menu": "The menu at {name} in {place}.",
    "pricing": "Prices at {name}. Ask us for a quote if what you need isn't listed.",
    "team": "The people behind {name}.",
    "gallery": "A look at {name} in {place}.",
    "testimonials": "What customers say about {name}.",
    "faq": "Answers to common questions about {name}.",
    "blog": "News and articles from {name}.",
    "blog-detail": "An article from {name}.",
    "booking": "Book with {name}: send a request and we'll confirm a time.",
    "contact": "Call, message or visit {name} in {place}.",
    "location": "Where to find {name} in {place}.",
    "events": "Planning something? Ask {name} about events.",
    "careers": "Working at {name}.",
    "terms": "The terms that apply when you use this website or book with {name}.",
    "other": "{label} at {name}.",
}


def _nav_label(info: dict[str, Any]) -> str:
    label = re.sub(r"\s+", " ", str(info.get("label") or "")).strip()
    if not label or len(label) > 40 or label.lower() in ("click here", "read more", "more"):
        label = humanize(str(info["path"]))
    return label[:40]


_SAFE_PATH = re.compile(r"^/[A-Za-z0-9._~!$&'()*+,;=:@%/-]*$")


def _redirect(redirects: list[Redirect], src: str, to: str) -> None:
    # Paths with characters a static host can't serve as a file name keep only the new page.
    if _SAFE_PATH.match(src) and src.rstrip("/") != to and ".." not in src:
        redirects.append(Redirect(from_path=src, to_path=to))


def plan_pages(
    inventory: list[dict[str, Any]],
    *,
    name: str,
    noun: str,
    place: str,
    available: list[SectionType],
    has_booking: bool = False,
) -> tuple[list[Page], list[Redirect]]:
    """One new page per page of the current site (home excluded: that's the spec itself).
    Old paths that change shape (legacy extensions, odd characters) get a redirect."""
    pages: list[Page] = []
    redirects: list[Redirect] = []
    taken = set(BUILTIN_PATHS)
    for info in inventory:
        src = str(info["path"])
        kind = str(info.get("kind") or classify(src, str(info.get("label") or "")))
        new_path = clean_path(src)
        if kind == "home" or new_path == "/":
            if src != "/":
                _redirect(redirects, src, "/")
            continue
        if kind == "privacy":
            # The template's own privacy page describes what the new site actually does.
            if src != "/privacy":
                _redirect(redirects, src, "/privacy")
            continue
        if kind not in _PLAN:
            kind = "other"
        if new_path in taken:
            if src != new_path:
                _redirect(redirects, src, new_path)
            continue
        taken.add(new_path)
        label = _nav_label(info)
        fill = {"name": name, "noun": noun, "place": place, "label": label}
        sections, holders = _PLAN[kind]
        placeholders = [h.format(**fill) for h in holders]
        if kind == "booking" and has_booking:
            placeholders = []
        parent = new_path.rsplit("/", 1)[0] or None
        pages.append(
            Page(
                path=new_path,
                kind=kind,
                nav_label=label,
                in_nav=parent is None and kind != "terms",
                parent=parent,
                title=f"{label} | {name}"[:70],
                description=(_INTRO[kind].format(**fill))[:170],
                heading=label if kind != "about" else f"About {name}",
                intro=_INTRO[kind].format(**fill),
                sections=[s for s in sections if s in available],
                placeholders=placeholders,
                source_path=src,
            )
        )
        if src != new_path:
            _redirect(redirects, src, new_path)
    # A nested page whose parent wasn't on the old site still gets listed under its parent's
    # path in the sitemap; there is simply no parent page to link back to.
    paths = {p.path for p in pages}
    for p in pages:
        if p.parent and p.parent not in paths:
            p.parent = None
    return pages, redirects


def expected_paths(inventory: list[dict[str, Any]]) -> list[str]:
    """Every original path the replacement site must answer."""
    return [str(p["path"]) for p in inventory if p.get("fetched", True)]


# ---------------------------------------------------------------------------
# Quality gate: does every original page answer on the preview?
# ---------------------------------------------------------------------------

_REFRESH = re.compile(
    r"""<meta[^>]+http-equiv=["']?refresh["']?[^>]+content=["']?\s*\d+\s*;\s*url=([^"'>\s]+)""",
    re.I,
)


async def check_parity(
    fetcher: Fetcher, preview_url: str, inventory: list[dict[str, Any]], spec: Any
) -> dict[str, Any]:
    """Request every original path on the deployed preview. A page counts as present when it
    answers 200, directly or through the redirect the builder wrote for a changed path."""
    base = preview_url.rstrip("/")
    new_path = {r.from_path: r.to_path for r in spec.redirects}
    for p in spec.pages:
        if p.source_path:
            new_path.setdefault(p.source_path, p.path)
    results: list[dict[str, Any]] = []
    for info in inventory:
        if not info.get("fetched", True):
            continue
        path = str(info["path"])
        target = new_path.get(path, path)
        res = await fetcher.get(base + path, check_robots=False)
        status = "ok" if res.ok else "missing"
        m = _REFRESH.search(res.text[:2000]) if res.ok else None
        if m:
            hop = await fetcher.get(urljoin(res.final_url, m.group(1)), check_robots=False)
            status = "redirect" if hop.ok else "missing"
        results.append(
            {
                "path": path,
                "label": info.get("label"),
                "kind": info.get("kind"),
                "new_path": target,
                "status": status,
                "http_status": res.status or None,
            }
        )
    missing = [r["path"] for r in results if r["status"] == "missing"]
    return {
        "expected": len(results),
        "present": len(results) - len(missing),
        "missing": missing,
        "pages": results,
    }
