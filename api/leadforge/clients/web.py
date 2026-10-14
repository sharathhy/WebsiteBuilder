"""Polite HTTP fetching for site crawls and audits.

robots.txt and Crawl-delay are honoured, each domain is rate-limited, responses are
size-capped, and every request carries a descriptive User-Agent with a contact URL.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from leadforge.fixtures import mock_world

PARKED_MARKERS = (
    "domain may be for sale",
    "this domain is for sale",
    "buy this domain",
    "parked free",
    "domain parking",
    "sedoparking",
    "hugedomains",
)
CHALLENGE_MARKERS = ("just a moment...", "challenge-platform", "cf-chl", "checking your browser")


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    headers: dict[str, str]
    text: str
    elapsed_ms: int
    bytes: int
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status < 400

    @property
    def is_challenge(self) -> bool:
        low = self.text[:5000].lower()
        server = self.headers.get("server", "").lower()
        return self.status in (403, 429, 503) and (
            "cloudflare" in server or any(m in low for m in CHALLENGE_MARKERS)
        )

    @property
    def is_parked(self) -> bool:
        low = self.text[:20000].lower()
        return any(m in low for m in PARKED_MARKERS)


@dataclass
class _DomainState:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_request: float = 0.0
    robots: RobotFileParser | None = None
    crawl_delay: float | None = None


class MockWebTransport(httpx.AsyncBaseTransport):
    """Serves fixture websites for `.example` domains and local previews from storage;
    everything else is unreachable."""

    def __init__(
        self, preview: Callable[[str], tuple[int, dict[str, str], bytes] | None] | None = None
    ) -> None:
        self.preview = preview

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if self.preview is not None:
            hit = self.preview(str(request.url))
            if hit is not None:
                status, headers, body = hit
                return httpx.Response(status, headers=headers, content=body, request=request)
        host = request.url.host
        if not host.endswith(".example"):
            raise httpx.ConnectError(f"mock web: no route to {host}", request=request)
        status, headers, text = mock_world.mock_site_response(str(request.url))
        return httpx.Response(status, headers=headers, text=text, request=request)


class WebFetcher:
    def __init__(
        self,
        user_agent: str,
        *,
        timeout_s: float = 15.0,
        min_delay_s: float = 1.0,
        max_bytes: int = 3_000_000,
        transport: httpx.AsyncBaseTransport | None = None,
        respect_delays: bool = True,
    ) -> None:
        self.user_agent = user_agent
        self.min_delay_s = min_delay_s
        self.max_bytes = max_bytes
        self.respect_delays = respect_delays
        self.client = httpx.AsyncClient(
            timeout=timeout_s,
            follow_redirects=True,
            headers={"User-Agent": user_agent, "Accept": "text/html,*/*;q=0.8"},
            transport=transport,
            max_redirects=5,
        )
        self._domains: dict[str, _DomainState] = {}

    def _state(self, url: str) -> _DomainState:
        host = urlsplit(url).netloc.lower()
        return self._domains.setdefault(host, _DomainState())

    async def _load_robots(self, url: str, state: _DomainState) -> None:
        parts = urlsplit(url)
        robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
        parser = RobotFileParser()
        try:
            resp = await self.client.get(robots_url)
            if resp.status_code >= 400:
                parser.parse([])  # no robots.txt => allowed
            else:
                parser.parse(resp.text.splitlines())
        except httpx.HTTPError:
            parser.parse([])
        state.robots = parser
        delay = parser.crawl_delay(self.user_agent)
        state.crawl_delay = float(delay) if delay is not None else None

    async def allowed(self, url: str) -> bool:
        state = self._state(url)
        if state.robots is None:
            await self._load_robots(url, state)
        assert state.robots is not None
        return state.robots.can_fetch(self.user_agent, url)

    def crawl_delay(self, url: str) -> float | None:
        return self._state(url).crawl_delay

    async def get(self, url: str, *, check_robots: bool = True) -> FetchResult:
        state = self._state(url)
        if check_robots and not await self.allowed(url):
            return FetchResult(url, url, 0, {}, "", 0, 0, error="blocked_by_robots")
        async with state.lock:
            if self.respect_delays:
                delay = max(self.min_delay_s, state.crawl_delay or 0)
                wait = state.last_request + delay - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
            started = time.monotonic()
            try:
                resp = await self.client.get(url)
                raw = resp.content[: self.max_bytes]
                text = raw.decode(resp.encoding or "utf-8", errors="replace")
                return FetchResult(
                    url=url,
                    final_url=str(resp.url),
                    status=resp.status_code,
                    headers={k.lower(): v for k, v in resp.headers.items()},
                    text=text,
                    elapsed_ms=int((time.monotonic() - started) * 1000),
                    bytes=len(resp.content),
                )
            except httpx.TimeoutException:
                return FetchResult(url, url, 0, {}, "", 0, 0, error="timeout")
            except httpx.HTTPError as exc:
                return FetchResult(url, url, 0, {}, "", 0, 0, error=f"unreachable: {exc}")
            finally:
                state.last_request = time.monotonic()

    async def aclose(self) -> None:
        await self.client.aclose()
