"""Serving locally "deployed" preview sites (mock deploy target) from storage."""

import mimetypes
from pathlib import Path

from leadforge.core.config import Settings

PREVIEW_PREFIX = "/previews/"


def preview_root(settings: Settings) -> Path:
    return settings.storage_dir / "previews"


def resolve_preview_file(settings: Settings, slug: str, path: str) -> Path | None:
    root = (preview_root(settings) / slug).resolve()
    target = (root / path.lstrip("/")).resolve()
    if not str(target).startswith(str(root)):
        return None
    if target.is_dir():
        target = target / "index.html"
    elif not target.exists() and not target.suffix:
        alt = target.with_suffix(".html")
        target = alt if alt.exists() else target / "index.html"
    return target if target.is_file() else None


def preview_response(settings: Settings, url: str) -> tuple[int, dict[str, str], bytes] | None:
    """Return a response for a preview URL under PUBLIC_BASE_URL, or None if not a preview."""
    base = settings.public_base_url.rstrip("/") + PREVIEW_PREFIX
    if not url.startswith(base):
        return None
    rest = url[len(base) :].split("?", 1)[0].split("#", 1)[0]
    slug, _, path = rest.partition("/")
    file = resolve_preview_file(settings, slug, path)
    if file is None:
        not_found = resolve_preview_file(settings, slug, "404.html")
        body = not_found.read_bytes() if not_found else b"<h1>Not found</h1>"
        return 404, {"content-type": "text/html; charset=utf-8"}, body
    ctype = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
    if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
        ctype += "; charset=utf-8"
    headers = {
        "content-type": ctype,
        "x-robots-tag": "noindex, nofollow",
        "strict-transport-security": "max-age=31536000",
        "x-content-type-options": "nosniff",
        "content-security-policy": "frame-ancestors *; default-src * 'unsafe-inline' 'unsafe-eval' data: blob:",
    }
    return 200, headers, file.read_bytes()
