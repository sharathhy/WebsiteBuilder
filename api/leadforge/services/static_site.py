"""Built-in static renderer for a SiteSpec.

Fallback for environments without Node (and fast path for tests). It honours every
content rule and SEO/accessibility requirement of the Next.js templates, but has no
motion or 3D. The Next.js template library in templates/site is the primary builder.
"""

import html
import json
from pathlib import Path

from leadforge.schemas.site_spec import SiteSpec
from leadforge.services.brand import contrast

DAY_ABBR = {"Monday": "Mo", "Tuesday": "Tu", "Wednesday": "We", "Thursday": "Th",
            "Friday": "Fr", "Saturday": "Sa", "Sunday": "Su"}  # fmt: skip
SCHEMA_TYPE = {
    "clinic": "Dentist", "restaurant": "Restaurant", "salon": "BeautySalon",
    "fitness": "HealthClub", "legal-finance": "LegalService", "real-estate": "RealEstateAgent",
    "home-services": "HomeAndConstructionBusiness", "generic-premium": "LocalBusiness",
}  # fmt: skip


def e(text: object) -> str:
    return html.escape(str(text), quote=True)


def jsonld(spec: SiteSpec) -> dict[str, object]:
    b = spec.business
    data: dict[str, object] = {
        "@context": "https://schema.org",
        "@type": SCHEMA_TYPE.get(spec.template, "LocalBusiness"),
        "name": b.name,
        "url": spec.site_url,
        "description": b.description,
        "address": {
            "@type": "PostalAddress", "streetAddress": b.address.street,
            "addressLocality": b.address.city, "addressRegion": b.address.state,
            "addressCountry": b.address.country,
        },
    }  # fmt: skip
    if b.phone_e164:
        data["telephone"] = b.phone_e164
    if b.lat is not None and b.lng is not None:
        data["geo"] = {"@type": "GeoCoordinates", "latitude": b.lat, "longitude": b.lng}
    if b.hours:
        data["openingHoursSpecification"] = [
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": h.day,
                "opens": h.opens,
                "closes": h.closes,
            }
            for h in b.hours
        ]
    if b.rating is not None and b.review_count:
        data["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": b.rating,
            "reviewCount": b.review_count,
        }
    if b.socials:
        data["sameAs"] = [str(s.url) for s in b.socials]
    return data


def _css(spec: SiteSpec) -> str:
    t = spec.theme
    on_primary = "#ffffff" if contrast(t.primary, "#ffffff") >= 4.5 else "#0f172a"
    return f"""
:root{{--p:{t.primary};--s:{t.secondary};--a:{t.accent};--bg:{t.background};--fg:{t.foreground};--on-p:{on_primary};--r:{t.radius_px}px}}
*{{box-sizing:border-box}}html{{-webkit-text-size-adjust:100%}}
body{{margin:0;font:400 clamp(1rem,.95rem + .25vw,1.125rem)/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--fg);background:var(--bg)}}
img{{max-width:100%;height:auto;display:block}}a{{color:var(--p)}}
.skip{{position:absolute;left:-999px}}.skip:focus{{left:1rem;top:1rem;background:#fff;padding:.5rem;z-index:9}}
:focus-visible{{outline:3px solid var(--a);outline-offset:2px}}
.wrap{{width:min(1120px,100% - 2rem);margin-inline:auto}}
header.top{{position:sticky;top:0;background:rgba(255,255,255,.92);backdrop-filter:blur(8px);border-bottom:1px solid #e5e7eb;z-index:5}}
header.top .wrap{{display:flex;align-items:center;justify-content:space-between;min-height:60px;gap:1rem}}
.brand{{font-weight:700;color:var(--s);text-decoration:none}}
.btn{{display:inline-flex;align-items:center;justify-content:center;min-height:48px;min-width:48px;padding:.75rem 1.25rem;border-radius:var(--r);background:var(--p);color:var(--on-p);font-weight:600;text-decoration:none;border:0;cursor:pointer;font-size:1rem}}
.btn.ghost{{background:transparent;color:var(--s);box-shadow:inset 0 0 0 2px var(--s)}}
.hero{{position:relative;overflow:hidden;color:#fff;background:var(--s)}}
.hero img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
.hero .wrap{{position:relative;padding:clamp(4rem,12vw,9rem) 0}}
.hero .card{{max-width:40rem;background:rgba(15,23,42,.55);backdrop-filter:blur(6px);padding:clamp(1.25rem,4vw,2.5rem);border-radius:calc(var(--r) * 1.5)}}
h1{{font-size:clamp(2rem,1.4rem + 3vw,3.5rem);line-height:1.1;margin:0 0 1rem}}
h2{{font-size:clamp(1.5rem,1.2rem + 1.5vw,2.25rem);line-height:1.2;margin:0 0 1rem;color:var(--s)}}
section{{padding:clamp(3rem,8vw,6rem) 0}}section:nth-of-type(even){{background:#f8fafc}}
.grid{{display:grid;gap:1rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr))}}
.tile{{background:#fff;border:1px solid #e5e7eb;border-radius:var(--r);padding:1.25rem;box-shadow:0 1px 2px rgba(0,0,0,.04)}}
.tile h3{{margin:.25rem 0 .5rem;font-size:1.125rem}}
.rating{{font-size:clamp(2.5rem,2rem + 2vw,3.5rem);font-weight:800;color:var(--s)}}
table{{border-collapse:collapse;width:100%;max-width:28rem}}td,th{{padding:.5rem;border-bottom:1px solid #e5e7eb;text-align:left}}
details{{border-bottom:1px solid #e5e7eb;padding:.75rem 0}}summary{{cursor:pointer;font-weight:600;min-height:44px;display:flex;align-items:center}}
form{{display:grid;gap:.75rem;max-width:36rem}}label{{display:grid;gap:.25rem;font-weight:600}}
input,textarea{{font:inherit;padding:.75rem;border:1px solid #94a3b8;border-radius:calc(var(--r) / 2);min-height:48px}}
.hp{{position:absolute;left:-5000px}}
.note{{background:#fef3c7;color:#78350f;padding:.75rem 1rem;font-size:.9rem}}
footer{{background:var(--s);color:#e2e8f0;padding:2.5rem 0 6rem}}footer a{{color:#fff}}
.callbar{{position:fixed;inset:auto 0 0 0;display:grid;grid-auto-flow:column;gap:.5rem;padding:.5rem;background:#fff;border-top:1px solid #e5e7eb;z-index:6}}
.callbar .btn{{width:100%}}
@media (min-width:768px){{.callbar{{display:none}}footer{{padding-bottom:2.5rem}}}}
@media (prefers-reduced-motion:no-preference){{.btn{{transition:transform .15s}}.btn:hover{{transform:translateY(-1px)}}}}
"""


def _head(spec: SiteSpec, title: str, description: str, path: str = "") -> str:
    robots = "noindex,nofollow" if spec.noindex else "index,follow"
    url = spec.site_url.rstrip("/") + "/" + path
    og = spec.site_url.rstrip("/") + "/generated/og.svg"
    return (
        f'<!doctype html><html lang="{spec.locale}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{e(title)}</title><meta name="description" content="{e(description)}">'
        f'<meta name="robots" content="{robots}"><link rel="canonical" href="{e(url)}">'
        f'<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}">'
        f'<meta property="og:type" content="website"><meta property="og:url" content="{e(url)}">'
        f'<meta property="og:image" content="{e(og)}"><meta name="theme-color" content="{spec.theme.primary}">'
        '<link rel="icon" href="favicon.svg" type="image/svg+xml"><link rel="manifest" href="manifest.webmanifest">'
        f"<style>{_css(spec)}</style></head>"
    )


def render_index(spec: SiteSpec) -> str:
    b = spec.business
    phone = b.phone_display or b.phone_e164
    parts: list[str] = [_head(spec, spec.seo.title, spec.seo.description)]
    parts.append('<body><a class="skip" href="#main">Skip to content</a>')
    if spec.placeholders:
        parts.append(
            '<div class="note" role="note"><div class="wrap"><strong>Preview.</strong> Items to '
            "confirm with the owner: " + e(", ".join(spec.placeholders)) + "</div></div>"
        )
    cta = spec.hero.cta_primary
    parts.append(
        f'<header class="top"><div class="wrap"><a class="brand" href="./">{e(b.name)}</a>'
        f'<a class="btn" href="{e(cta.href)}">{e(cta.label)}</a></div></header><main id="main">'
    )
    img = spec.hero.fallback_image
    second = spec.hero.cta_secondary
    parts.append(
        f'<div class="hero"><img src="{e(img.src)}" alt="{e(img.alt)}" width="1600" height="900" '
        f'fetchpriority="high"><div class="wrap"><div class="card"><p>{e(b.tagline)}</p>'
        f"<h1>{e(spec.hero.headline)}</h1><p>{e(spec.hero.subheadline)}</p>"
        f'<p style="display:flex;flex-wrap:wrap;gap:.75rem"><a class="btn" href="{e(cta.href)}">{e(cta.label)}</a>'
        + (
            f'<a class="btn ghost" style="color:#fff;box-shadow:inset 0 0 0 2px #fff" href="{e(second.href)}">{e(second.label)}</a>'
            if second
            else ""
        )
        + "</p></div></div></div>"
    )
    for section in spec.sections:
        if section == "services" and spec.services:
            tiles = "".join(
                f'<div class="tile"><h3>{e(s.title)}</h3><p>{e(s.description)}</p>'
                + (f"<p><strong>{e(s.price)}</strong></p>" if s.price else "")
                + "</div>"
                for s in spec.services
            )
            parts.append(
                f'<section id="services"><div class="wrap"><h2>Services</h2><div class="grid">{tiles}</div></div></section>'
            )
        elif section == "about" and spec.about:
            parts.append(
                f'<section id="about"><div class="wrap"><h2>{e(spec.about.heading)}</h2><p>{e(spec.about.body)}</p></div></section>'
            )
        elif section == "social_proof" and spec.social_proof.rating:
            sp = spec.social_proof
            link = (
                f' <a href="{e(sp.source_url)}">Read the reviews on Google</a>'
                if sp.source_url
                else ""
            )
            quotes = "".join(
                f'<blockquote class="tile"><p>“{e(t.quote)}”</p><footer>{e(t.author)}, {e(t.source)}</footer></blockquote>'
                for t in sp.testimonials
            )
            parts.append(
                f'<section id="reviews"><div class="wrap"><h2>What customers say</h2>'
                f'<p class="rating">{sp.rating:.1f}★</p><p>Rated {sp.rating:.1f} out of 5 from '
                f"{sp.review_count or 0} reviews on {e(sp.source)}.{link}</p>{quotes}</div></section>"
            )
        elif section == "gallery" and spec.gallery:
            figs = "".join(
                f'<figure class="tile"><img src="{e(g.src)}" alt="{e(g.alt)}" width="800" height="600" loading="lazy">'
                + (f"<figcaption><small>{e(g.credit)}</small></figcaption>" if g.credit else "")
                + "</figure>"
                for g in spec.gallery
            )
            parts.append(
                f'<section id="gallery"><div class="wrap"><h2>Gallery</h2><div class="grid">{figs}</div></div></section>'
            )
        elif section == "hours" and b.hours:
            rows = "".join(
                f'<tr><th scope="row">{e(h.day)}</th><td>{e(h.opens)}–{e(h.closes)}</td></tr>'
                for h in b.hours
            )
            parts.append(
                f'<section id="hours"><div class="wrap"><h2>Opening hours</h2><table>{rows}</table></div></section>'
            )
        elif section == "map" and b.lat is not None:
            maps = b.google_maps_url or f"https://www.google.com/maps?q={b.lat},{b.lng}"
            parts.append(
                f'<section id="map"><div class="wrap"><h2>Find us</h2><p>{e(b.address.street)}, {e(b.address.city)}</p>'
                f'<p><a class="btn" href="{e(maps)}">Open in Google Maps</a></p></div></section>'
            )
        elif section == "faq" and spec.faq:
            qs = "".join(
                f"<details><summary>{e(f.q)}</summary><p>{e(f.a)}</p></details>" for f in spec.faq
            )
            parts.append(
                f'<section id="faq"><div class="wrap"><h2>Questions</h2>{qs}</div></section>'
            )
        elif section == "contact":
            c = spec.contact
            booking = (
                f'<p><a class="btn" href="{e(c.booking_url)}">Book online</a></p>'
                if c.booking_url
                else ""
            )
            parts.append(
                f'<section id="contact"><div class="wrap"><h2>Contact us</h2>{booking}'
                f'<form method="post" action="{e(c.form_endpoint)}" data-site="{e(c.site_id)}">'
                f'<input type="hidden" name="site_id" value="{e(c.site_id)}">'
                '<label>Name<input name="name" required autocomplete="name"></label>'
                '<label>Email<input name="email" type="email" required autocomplete="email"></label>'
                '<label>Phone<input name="phone" type="tel" autocomplete="tel"></label>'
                '<label>Message<textarea name="message" rows="4" required></textarea></label>'
                '<label class="hp" aria-hidden="true">Website<input name="company_website" tabindex="-1" autocomplete="off"></label>'
                '<button class="btn" type="submit">Send message</button></form></div></section>'
            )
    parts.append("</main>")
    from datetime import UTC, datetime

    year_note = f"© {datetime.now(UTC).year} " + e(b.name)
    parts.append(
        f'<footer><div class="wrap"><p><strong>{e(b.name)}</strong><br>{e(b.address.street)}, {e(b.address.city)}'
        + (f", {e(b.address.state)}" if b.address.state else "")
        + "</p>"
        + (f'<p>Phone: <a href="tel:{e(b.phone_e164)}">{e(phone)}</a></p>' if b.phone_e164 else "")
        + f'<p><a href="privacy/">Privacy policy</a></p><p><small>{year_note}. '
        + e(" · ".join(spec.attribution))
        + "</small></p></div></footer>"
    )
    bar = []
    if b.phone_e164:
        bar.append(f'<a class="btn" href="tel:{e(b.phone_e164)}">Call</a>')
    if b.whatsapp_e164:
        bar.append(
            f'<a class="btn ghost" href="https://wa.me/{e(b.whatsapp_e164.lstrip("+"))}">WhatsApp</a>'
        )
    if bar:
        parts.append('<nav class="callbar" aria-label="Quick contact">' + "".join(bar) + "</nav>")
    parts.append(
        f'<script type="application/ld+json">{json.dumps(jsonld(spec))}</script></body></html>'
    )
    return "".join(parts)


def render_privacy(spec: SiteSpec) -> str:
    b = spec.business
    contact = f" or call {e(b.phone_display or b.phone_e164)}" if b.phone_e164 else ""
    return (
        _head(
            spec,
            f"Privacy policy | {b.name}",
            f"How {b.name} handles your information.",
            "privacy/",
        )
        + f'<body><main class="wrap" style="padding:3rem 0"><h1>Privacy policy</h1>'
        f"<p>When you contact {e(b.name)} through this website, we use the details you send "
        "(name, email, phone, message) only to reply to you. We don't sell or share them.</p>"
        "<p>This site does not use advertising cookies. Analytics are off unless enabled by the owner.</p>"
        f"<p>To ask about or delete your data, message us through the contact form{contact}.</p>"
        '<p><a href="../">Back to home</a></p></main></body></html>'
    )


def write_site(spec: SiteSpec, out: Path, assets: dict[str, bytes]) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(render_index(spec), encoding="utf-8")
    (out / "privacy").mkdir(exist_ok=True)
    (out / "privacy" / "index.html").write_text(render_privacy(spec), encoding="utf-8")
    (out / "404.html").write_text(
        _head(spec, "Page not found", "This page doesn't exist.")
        + '<body><main class="wrap" style="padding:3rem 0"><h1>Page not found</h1>'
        '<p><a class="btn" href="./">Go to the homepage</a></p></main></body></html>',
        encoding="utf-8",
    )
    gen = out / "generated"
    gen.mkdir(exist_ok=True)
    for name, data in assets.items():
        (gen / name).write_bytes(data)
    initials = "".join(w[0] for w in spec.business.name.split()[:2]).upper()
    (out / "favicon.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="{spec.theme.primary}"/>'
        f'<text x="32" y="42" font-family="system-ui" font-size="28" font-weight="700" fill="#fff" text-anchor="middle">{e(initials)}</text></svg>'
    )
    (out / "manifest.webmanifest").write_text(json.dumps({
        "name": spec.business.name, "short_name": spec.business.name[:12], "start_url": "./",
        "display": "standalone", "theme_color": spec.theme.primary, "background_color": "#ffffff",
        "icons": [{"src": "favicon.svg", "sizes": "any", "type": "image/svg+xml"}],
    }))  # fmt: skip
    base = spec.site_url.rstrip("/")
    (out / "robots.txt").write_text(
        "User-agent: *\nDisallow: /\n"
        if spec.noindex
        else f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n"
    )
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{e(base)}/</loc></url><url><loc>{e(base)}/privacy/</loc></url></urlset>"
    )
    return out
