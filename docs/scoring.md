# Scoring rubric (v1.0.0)

Every audit produces a 0 to 100 score, a grade and the evidence behind each point.
The rubric lives in `api/leadforge/scoring/rubric.py`; bump `RUBRIC_VERSION` whenever a
weight or threshold changes, because cached audits are only reused for the same version.

| Category | Points | Checks |
| --- | --- | --- |
| Performance | 20 | LCP, interactivity (INP, or TBT when INP is missing), CLS, page weight, Lighthouse performance (70% mobile, 30% desktop) |
| SEO | 15 | title, meta description, canonical, sitemap, robots.txt, LocalBusiness JSON-LD, Open Graph, image alt text, indexable |
| Mobile | 15 | viewport meta, no horizontal overflow at 360/390/768 px, tap targets at least 24 px (WCAG 2.2 minimum; 90% must pass for full points), text under 12 px on no more than 5% of elements |
| Visual design | 15 | modernity, typography, spacing, colour, hierarchy, imagery, consistency; each 0 to 5 from a vision review of the 1440 px and 390 px screenshots |
| Accessibility | 10 | Lighthouse accessibility plus axe-core serious/critical violations, page language, image alt text, form labels, named links and buttons |
| Trust | 10 | HTTPS, security headers, privacy page, name/address/phone shown, real reviews linked, copyright year current |
| Conversion | 10 | CTA above the fold, click-to-call, WhatsApp or booking, map, hours, pricing, contact form |
| Tech | 5 | broken links, outdated stack markers, console errors, page bloat |

Grades: **A** ≥ 85, **B** 70 to 84, **C** 50 to 69, **D** < 50. Sites under the rebuild
threshold (60 by default, per campaign) go to the generator.

Special cases:

- **No website:** score 0, grade D, straight to the rebuild queue.
- **Parked or unreachable domain:** treated as no website (score 0).
- **Bot wall (Cloudflare or similar):** the audit is marked failed with the reason. It is
  never bypassed, and the lead stays unscored.
- **Generated previews** are deliberately `noindex` until the client buys, so they don't
  lose the robots/indexable points. A local mock preview served over plain HTTP keeps the
  HTTPS points, because every real deploy target (Vercel) is HTTPS-only.

Determinism: the same site re-scored scores within ±3 points (enforced by
`api/tests/test_scoring.py`). The design review runs at a fixed prompt version and is
cached with the audit for 30 days.

Mock mode: with `MOCK_APIS=true`, PageSpeed numbers are estimated from the page itself
(`MockPsiClient`) and the design review uses page-structure heuristics. Real keys swap in
the live PageSpeed Insights API and Claude vision review without code changes.

## Quality gate for generated sites

A generated site goes live only when its own audit scores **≥ 90 and at least 30
points above the original**, and **every page of the original site answers on the
preview** (page parity). On a miss the generator retries with fixes (3D off, then
gallery off) up to 3 attempts, then marks the site **manual review** with every attempt's
score and reason.

### Page parity

During enrichment the crawler lists the current site's pages: links on the home page, one
level of links below each page, and the sitemap(s) named in robots.txt. Each candidate is
fetched through the same polite fetcher (robots.txt, crawl-delay, per-domain rate limit)
and kept only if it answers 200 with HTML; asset files, admin, login, cart and feed URLs
are ignored and the list is capped at `PAGE_INVENTORY_MAX` (30, home included). Only the
path, nav label, `<title>` and a page kind (about, services, menu, team, gallery, blog,
contact...) are stored on `websites.page_inventory`; page text is never stored.

The generator turns each entry into a `pages[]` item in the site spec (spec 1.1) at the
same path. Changed addresses (`/menu.html` to `/menu/`, `/privacy-policy` to the
template's `/privacy/`) get a redirect page in `redirects[]`. After deploying, the gate
requests every original path on the preview; the result (`expected`, `present`,
`missing`, per page `ok`/`redirect`/`missing`) is saved on `generated_sites.page_parity`
and shown on the lead screen. Any missing page fails the gate.
