"""Page parity: inventory of the current site, the planned pages and the gate check."""

from pathlib import Path

from leadforge.clients.web import MockWebTransport, WebFetcher
from leadforge.fixtures import mock_world as mw
from leadforge.pipeline.generate import gate
from leadforge.schemas.site_spec import SiteSpec
from leadforge.services import pages as P
from leadforge.services.static_site import write_site


def _domain(category: str, quality: str) -> str:
    for seq in range(1, 300):
        d = mw.site_slug(seq, category, "austin", "US") + ".example"
        if mw._business_from_domain(d)[1] == quality:
            return d
    raise AssertionError("no fixture with that quality")


def _fetcher() -> WebFetcher:
    return WebFetcher("LeadForgeBot/test", transport=MockWebTransport(), respect_delays=False)


def test_normalize_and_classify() -> None:
    base = "https://a.example/"
    assert P.normalize_path("/About/", base) == "/about"
    assert P.normalize_path("https://www.a.example/index.html", base) == "/"
    assert P.normalize_path("/menu.pdf", base) is None
    assert P.normalize_path("/wp-admin/x", base) is None
    assert P.normalize_path("https://other.example/about", base) is None
    assert P.normalize_path("mailto:x@a.example", base) is None
    assert P.classify("/gallery", "Lookbook") == "gallery"  # path wins over the label
    assert P.classify("/services/implants", "Implants") == "services-detail"
    assert P.classify("/reservations") == "booking"
    assert P.classify("/our-ethos") == "other"
    assert P.clean_path("/Price List.html".lower()) == "/price-list"


async def test_inventory_uses_links_and_sitemap_and_respects_robots() -> None:
    f = _fetcher()
    domain = _domain("dentists", "good")
    home = await f.get(f"https://{domain}/")
    pages, stats = await P.build_inventory(f, home)
    paths = [p.path for p in pages]
    assert paths[0] == "/"
    for want in ("/about", "/contact", "/services", "/services/teeth-whitening", "/blog"):
        assert want in paths
    assert "/private/staff" not in paths and stats["skipped_robots"] == 1
    assert stats["in_sitemap"] >= len(paths) - 1
    # Structure only: no page text is kept.
    assert set(pages[1].as_dict()) == {
        "path",
        "label",
        "kind",
        "title",
        "source",
        "status",
        "fetched",
    }
    await f.aclose()


async def test_inventory_is_capped() -> None:
    f = _fetcher()
    home = await f.get(f"https://{_domain('dentists', 'good')}/")
    pages, stats = await P.build_inventory(f, home, max_pages=4)
    assert len(pages) == 4 and stats["truncated"]
    await f.aclose()


def test_plan_pages_rewrites_and_marks_placeholders() -> None:
    inventory = [
        {"path": "/", "label": "Home", "kind": "home"},
        {"path": "/menu.html", "label": "Our menu", "kind": "menu"},
        {"path": "/services", "label": "Treatments", "kind": "services"},
        {"path": "/services/implants", "label": "Implants", "kind": "services-detail"},
        {"path": "/privacy-policy", "label": "Privacy", "kind": "privacy"},
        {"path": "/team", "label": "Click here", "kind": "team"},
    ]
    pages, redirects = P.plan_pages(
        inventory, name="Sample Co", noun="dentist", place="Austin",
        available=["services", "faq", "contact", "hours"],
    )  # fmt: skip
    by_path = {p.path: p for p in pages}
    assert set(by_path) == {"/menu", "/services", "/services/implants", "/team"}
    assert by_path["/menu"].placeholders and "copy" in by_path["/menu"].placeholders[0]
    assert by_path["/services/implants"].parent == "/services"
    assert not by_path["/services/implants"].in_nav
    assert by_path["/team"].nav_label == "Team"  # unhelpful link text replaced
    assert "map" not in by_path["/menu"].sections  # no data, no section
    assert {(r.from_path, r.to_path) for r in redirects} == {
        ("/menu.html", "/menu"),
        ("/privacy-policy", "/privacy"),
    }


def test_gate_fails_on_missing_pages() -> None:
    ok, why = gate(96, 20, ["/menu", "/team"])
    assert not ok and why and "/menu" in why
    assert gate(96, 20, [])[0]


def test_static_builder_writes_every_page_and_redirect(tmp_path: Path) -> None:
    example = Path(__file__).resolve().parents[2] / "templates" / "examples"
    raw = next(example.glob("*.json")).read_text()
    spec = SiteSpec.model_validate_json(raw)
    pages, redirects = P.plan_pages(
        [{"path": "/menu.html", "label": "Menu", "kind": "menu"},
         {"path": "/services", "label": "Services", "kind": "services"},
         {"path": "/services/a", "label": "A", "kind": "services-detail"}],
        name=spec.business.name, noun="x", place="y", available=list(spec.sections),
    )  # fmt: skip
    spec = spec.model_copy(update={"pages": pages, "redirects": redirects})
    out = write_site(spec, tmp_path / "out", {})
    assert (out / "menu" / "index.html").exists()
    assert (out / "services" / "a" / "index.html").exists()
    stub = (out / "menu.html").read_text()
    assert 'http-equiv="refresh"' in stub and "url=menu/" in stub
    nested = (out / "services" / "a" / "index.html").read_text()
    assert 'href="../../favicon.svg"' in nested and "Placeholder" in nested
    assert "/services/a/" in (out / "sitemap.xml").read_text()
