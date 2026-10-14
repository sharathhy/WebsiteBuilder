"""Business deduplication: place_id first, then fuzzy name + phone + domain."""

import math
import re
import unicodedata
from urllib.parse import urlsplit

from rapidfuzz import fuzz
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from leadforge.models import Business

_STOP = {"the", "and", "pvt", "ltd", "llc", "inc", "co", "private", "limited", "&"}
_SUFFIX_RE = re.compile(r"\((?:[^)]*)\)")

NAME_THRESHOLD = 88
NEAR_METRES = 150


def normalize_name(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    text = _SUFFIX_RE.sub(" ", text)
    words = re.findall(r"[a-z0-9]+", text)
    return " ".join(w for w in words if w not in _STOP)


def domain_of(url: str | None) -> str | None:
    if not url:
        return None
    host = urlsplit(url if "://" in url else f"http://{url}").netloc.lower()
    host = host.split("@")[-1].split(":")[0]
    return host.removeprefix("www.") or None


def _distance_m(a: Business, b: Business) -> float | None:
    if None in (a.lat, a.lng, b.lat, b.lng):
        return None
    assert a.lat is not None and a.lng is not None and b.lat is not None and b.lng is not None
    r = 6_371_000
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dp, dl = p2 - p1, math.radians(b.lng - a.lng)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def is_same_business(a: Business, b: Business) -> bool:
    """Same phone or same domain plus a similar name, or a near-identical name next door."""
    score = fuzz.token_set_ratio(a.normalized_name, b.normalized_name)
    same_phone = bool(a.phone_e164 and a.phone_e164 == b.phone_e164)
    same_domain = bool(a.domain and a.domain == b.domain)
    dist = _distance_m(a, b)
    if (same_phone or same_domain) and score >= 70:
        return True
    return score >= 97 and dist is not None and dist <= NEAR_METRES


async def find_duplicate(db: AsyncSession, biz: Business) -> Business | None:
    """Return an earlier canonical business that `biz` duplicates, if any."""
    conds = []
    if biz.phone_e164:
        conds.append(Business.phone_e164 == biz.phone_e164)
    if biz.domain:
        conds.append(Business.domain == biz.domain)
    conds.append(Business.normalized_name == biz.normalized_name)
    stmt = select(Business).where(
        Business.id != biz.id,
        Business.city == biz.city,
        Business.duplicate_of_id.is_(None),
        or_(*conds),
    )
    for candidate in await db.scalars(stmt):
        if is_same_business(biz, candidate):
            return candidate
    return None
