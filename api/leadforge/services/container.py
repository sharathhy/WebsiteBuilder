"""Builds external-service clients once per process. MOCK_APIS swaps in fixtures.

Live clients are only used when MOCK_APIS=false AND the relevant key is set, so a
missing key can never silently turn into a paid call.
"""

from dataclasses import dataclass
from functools import partial

from leadforge.clients import dns as dns_client
from leadforge.clients.browser import BrowserProbe
from leadforge.clients.deploy import Deployer, LocalPreviewDeployer, VercelDeployer
from leadforge.clients.email import EmailSender, MockSender, ResendSender
from leadforge.clients.llm import AnthropicLLM, LLMClient, MockLLM
from leadforge.clients.places import GooglePlacesClient, MockPlacesClient, PlacesClient
from leadforge.clients.psi import GooglePsiClient, MockPsiClient, PsiClient
from leadforge.clients.web import MockWebTransport, WebFetcher
from leadforge.core.config import Settings, get_settings
from leadforge.fixtures import mock_world
from leadforge.services.contacts import MxResolver
from leadforge.services.previews import preview_response


@dataclass
class Services:
    settings: Settings
    places: PlacesClient
    fetcher: WebFetcher
    mx_resolver: MxResolver
    psi: PsiClient
    browser: BrowserProbe
    llm: LLMClient
    deployer: Deployer
    sender: EmailSender

    @property
    def mock(self) -> bool:
        return self.settings.mock_apis


_services: Services | None = None


def get_services() -> Services:
    global _services
    if _services is None:
        _services = build_services(get_settings())
    return _services


def set_services(services: Services | None) -> None:
    global _services
    _services = services


def _secret(value: object) -> str | None:
    getter = getattr(value, "get_secret_value", None)
    return getter() if getter else None


def build_services(settings: Settings) -> Services:
    mock = settings.mock_apis
    preview = partial(preview_response, settings)

    def browser_resolver(url: str) -> tuple[int, dict[str, str], bytes] | None:
        hit = preview(url)
        if hit is not None:
            return hit
        host = url.split("://", 1)[-1].split("/", 1)[0]
        if host.endswith(".example"):
            status, headers, body = mock_world.mock_site_response(url)
            return status, headers, body.encode()
        return None

    places_key = _secret(settings.google_places_api_key)
    llm_key = _secret(settings.anthropic_api_key)
    vercel_token = _secret(settings.vercel_token)
    resend_key = _secret(settings.resend_api_key)

    return Services(
        settings=settings,
        places=GooglePlacesClient(places_key) if not mock and places_key else MockPlacesClient(),
        fetcher=WebFetcher(
            settings.crawler_user_agent,
            timeout_s=settings.crawler_timeout_s,
            min_delay_s=settings.crawler_min_delay_s,
            max_bytes=settings.crawler_max_bytes,
            transport=MockWebTransport(preview) if mock else None,
            respect_delays=not mock,
        ),
        mx_resolver=dns_client.mock_has_mx if mock else dns_client.has_mx,
        psi=MockPsiClient(asset_bytes=partial(_preview_bytes, settings))
        if mock
        else GooglePsiClient(_secret(settings.google_psi_api_key)),
        browser=BrowserProbe(resolver=browser_resolver, offline=mock),
        llm=AnthropicLLM(llm_key, settings.llm_model, settings.llm_effort)
        if not mock and llm_key
        else MockLLM(),
        deployer=VercelDeployer(vercel_token)
        if not mock and vercel_token
        else LocalPreviewDeployer(settings),
        sender=ResendSender(resend_key) if not mock and resend_key else MockSender(settings),
    )


def _preview_bytes(settings: Settings, url: str) -> int | None:
    """For local previews, page weight = HTML + the JS/CSS it references (what PSI would see)."""
    import re

    hit = preview_response(settings, url)
    if hit is None or hit[0] != 200:
        return None
    html = hit[2].decode(errors="replace")
    total = len(hit[2])
    base = url.rsplit("/", 1)[0] + "/"
    for ref in re.findall(r'(?:src|href)="([^"]+\.(?:js|css|woff2))"', html):
        absolute = (
            ref
            if "://" in ref
            else (settings.public_base_url.rstrip("/") + ref if ref.startswith("/") else base + ref)
        )
        asset = preview_response(settings, absolute)
        if asset and asset[0] == 200:
            total += len(asset[2])
    return total
