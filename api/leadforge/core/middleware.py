"""Request IDs, access logs and security headers for every API response."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = logging.getLogger("leadforge.http")
request_id: ContextVar[str | None] = ContextVar("request_id", default=None)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}
# Docs pages and previews/forms bring their own policies.
SKIP_CSP = ("/api/docs", "/previews/", "/u/")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        rid = rid[:64]
        token = request_id.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id.reset(token)
        elapsed = round((time.perf_counter() - start) * 1000, 1)
        response.headers["X-Request-ID"] = rid
        path = request.url.path
        for key, value in SECURITY_HEADERS.items():
            if key == "Content-Security-Policy" and path.startswith(SKIP_CSP):
                continue
            if key == "X-Frame-Options" and path.startswith("/previews/"):
                continue  # previews are shown in the dashboard iframe
            response.headers.setdefault(key, value)
        if not path.startswith("/health"):
            log.info(
                "request",
                extra={"request_id": rid, "method": request.method, "path": path,
                       "status": response.status_code, "ms": elapsed},
            )  # fmt: skip
        return response
