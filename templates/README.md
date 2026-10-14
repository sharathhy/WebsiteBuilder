# templates/ — generated-site templates (Phase 5)

One Next.js project (`site/`) renders **any** business website from a JSON **site spec**.
The spec is the only input: no LLM, no runtime code generation. The contract is
[`site-spec.schema.json`](site-spec.schema.json), generated from the Pydantic model
`api/leadforge/schemas/site_spec.py` (don't edit the schema by hand).

```
templates/
  site-spec.schema.json   contract (generated from Pydantic)
  examples/<template>.json one valid example spec per template (fictional businesses)
  site/                   Next.js 16 App Router + React 19 + Tailwind v4 static export
  lighthouserc.json       Lighthouse CI (mobile) against site/out
  screenshots/            reference screenshots of built examples
```

## Templates

The 8 templates are presets inside the one project (`site/src/lib/presets.ts`). `spec.template`
picks the preset; colours always come from `spec.theme`. Category → template mapping lives in
[`config/targets.yaml`](../config/targets.yaml).

| template | hero layout | cards | services | motion | default 3D model | JSON-LD `@type` |
|---|---|---|---|---|---|---|
| `restaurant` | full-bleed photo, serif headline, 3D on the right | glass | menu list with dotted price leaders | slow, elegant | `plate` | `Restaurant` (`CafeOrCoffeeShop` for cafés) |
| `clinic` | split: copy + rounded image card, soft glows | elevated | icon cards | gentle, quick | `tooth` | `Dentist` if dental, else `MedicalClinic` |
| `salon` | arch-masked portrait image, centred copy on mobile | glass | numbered | floaty | `droplet` | `BeautySalon` (`DaySpa`) |
| `fitness` | poster: huge uppercase headline, diagonal image, ticker | solid | numbered | snappy | `dumbbell` | `HealthClub` |
| `legal-finance` | split with offset frame, ruled grid background | outline | numbered | minimal | `pillar` | `LegalService` / `AccountingService` (by category) |
| `real-estate` | full-bleed with glass copy panel | glass | icon cards | measured | `house` | `RealEstateAgent` |
| `home-services` | split with accent block, call-first CTA | solid (accent border) | icon cards | snappy | `wrench` | `HomeAndConstructionBusiness` |
| `generic-premium` | centred stage, gradient headline, tilted image card | glass | icon cards | smooth | `orb` | `LocalBusiness` |

`hero.model` in the spec overrides the template default (when the field is absent the template
default is used). Service `icon` is any [lucide](https://lucide.dev/icons) name in kebab-case
(unknown names fall back to `sparkles`).

### How spec fields render

- **Sections** render in `spec.sections` order after the hero. A listed section with no content
  (no services, `about: null`, empty gallery/FAQ/pricing, no hours, no geo/maps URL) is omitted —
  never filled with invented content. Nav links only cover rendered sections.
- **social_proof** shows the real rating + review count (from `social_proof`, falling back to
  `business.rating/review_count`) linked to `source_url`/`google_maps_url`. Testimonials render
  only from `social_proof.testimonials`; if both are empty the section is omitted.
- **placeholders** → a clearly labelled, dismissible “Preview — items to confirm with the owner”
  banner. Missing service prices are omitted; a pricing tier with an empty price shows a dashed
  “To be confirmed” chip.
- **Prices** are free text: bare numbers are formatted with `currency` + `locale`
  (`1500` → `₹1,500`, `150000` → `₹1,50,000` for en-IN, `$85` for en-US); “From 180” → “From $180”.
- **Gallery** shows each image's `credit` (linked to `credit_url`).
- **Hours**: table with today highlighted and an “Open now / Closed now” badge, computed in the
  business's time zone (India → Asia/Kolkata; US → by state, default New York). Overnight slots
  (e.g. 19:00–01:00) are handled.
- **Map**: Google Maps iframe (`https://www.google.com/maps?q=LAT,LNG&output=embed`) loads only
  when the user clicks “Show map” or it scrolls near the viewport; fallback is a link to
  `google_maps_url`.
- **Contact form** POSTs JSON `{site_id, name, email, phone, message, company_website,
  turnstile_token}` to `contact.form_endpoint` exactly as given. `company_website` is a hidden
  honeypot. Cloudflare Turnstile loads lazily only when `turnstile_site_key` is set.
  `booking_url` adds a “Book an appointment” button and a “Book” action on mobile.
- **pages** (spec 1.1, page parity): one inner page per page of the business's current site,
  rendered by `src/app/[...slug]/page.tsx` at `path` with a breadcrumb, `heading`, `intro`, child
  pages (`parent`), each of `placeholders` as a dashed “Placeholder — to be supplied by …” card,
  then the listed `sections`. When pages exist the header menu lists `in_nav` pages (instead of
  home-page anchors) and the footer lists all pages; the sitemap includes them. A spec with no
  pages builds a one-page site (`scripts/postbuild.mjs` removes the stub route static export
  needs). `redirects` are written by the LeadForge builder after the build as small redirect
  pages at the old addresses (e.g. `/menu.html` → `/menu/`).
- **Mobile action bar**: sticky Call / WhatsApp / Book — only for actions present in the spec.
- **Footer**: NAP (name, address, phone exactly as in `business`), socials, privacy link,
  `attribution` lines.
- **SEO**: title/description/keywords from `seo`; canonical, OG and sitemap URLs are absolute
  from `site_url`; JSON-LD `LocalBusiness` subtype (+ `FAQPage` when FAQ is shown) with address,
  telephone, geo, `openingHoursSpecification`, `aggregateRating` (only with a real rating and
  review count), `sameAs`. `noindex: true` → `<meta name="robots" content="noindex,nofollow">` on
  every page and `robots.txt` `Disallow: /`; otherwise `Allow: /` + `Sitemap:`.
- **Analytics**: `src/lib/analytics.ts` `track()` is a no-op unless `analytics.enabled` (Plausible
  or GA4, script injected after idle). Clicks on `[data-track]` elements are tracked.
- **Fonts**: `theme.font_heading` / `font_body` are self-hosted when bundled (Inter, Manrope,
  Fraunces, Playfair Display, Space Grotesk, Outfit, Oswald, Source Serif 4, DM Sans — latin +
  latin-ext subsets only). Any other name falls back to the template's system font stack.

## Building a site

```bash
cd templates/site
npm ci
SITE_SPEC=/abs/path/to/spec.json npm run build        # → templates/site/out/
npm run check:budget                                  # first-load JS budget (fails > 250 KB gz)
```

- `SITE_SPEC` — absolute path to the spec (default `templates/site/site.json`, a copy of the clinic
  example). `npm run build` first runs `scripts/prepare-spec.mjs`, which validates the spec against
  `../site-spec.schema.json` (override with `SITE_SPEC_SCHEMA`) and fails the build on errors.
- `BASE_PATH` — optional sub-path, e.g. `BASE_PATH=/previews/sample-dental-1a2b`. Wired to Next's
  `basePath` + `assetPrefix`; internal links, fonts, favicon, manifest, OG image and local
  `/samples` / `/assets` images are prefixed. `site_url` must already include the sub-path
  (absolute URLs are built by appending to it). Unset → served from `/`.
- `SITE_ASSETS_DIR` — optional directory copied to `out/assets/`; reference files in the spec as
  `/assets/<file>`. Spec paths starting with `/samples/` resolve to `site/sample-assets/` (the
  sample artwork used by the examples).
- Output (`out/`): `index.html`, `privacy/index.html`, `404.html`, `sitemap.xml`, `robots.txt`,
  `manifest.webmanifest`, `favicon.svg` (initials + theme colour), `icon-512.png`, `og.png`
  (1200×630, rendered at build). Builds are offline after `npm ci` (no remote fonts or images).
- One build at a time per checkout (`.next/`, `public/fonts`, `public/samples` are rewritten per
  build). For parallel builds, copy `site/` (without `out/`, `.next/`) per job.

Other scripts: `npm run lint`, `npm run typecheck`, `npm test` (vitest: schema validation of all
examples, JSON-LD, contrast, price/time formatting, overnight hours, sub-path URLs).

Build every example:

```bash
cd templates/site
for f in ../examples/*.json; do SITE_SPEC=$(realpath "$f") npm run build && npm run check:budget || exit 1; done
```

## Motion, layers and 3D

- **Lenis** smooth scroll + **GSAP ScrollTrigger** (loaded by dynamic import after idle): parallax
  layers (`data-speed`), the pinned services story on desktop (intro column pinned, progress rail,
  cards rising out of z-depth via `data-depth`), and the generic-premium tilted image card
  (`data-tilt`).
- **Motion** (`motion/react`, `LazyMotion` with async `domAnimation`) for entrance reveals,
  staggered cards and hover lift; `MotionConfig reducedMotion="user"`.
- **3D hero** (React Three Fiber + drei): one procedural scene per `hero.model` — `tooth`, `plate`,
  `droplet`, `dumbbell`, `pillar`, `house`, `wrench`, `orb` — built from primitives,
  `LatheGeometry` and `ExtrudeGeometry`; lighting from local `Lightformer`s (no HDR downloads).
  Loaded with `next/dynamic({ ssr: false })` only after window `load` + `requestIdleCallback` and
  only while the hero is visible (IntersectionObserver); the render loop pauses off-screen.

- **Scroll showcase** (`hero.scroll_scene`, default on; off whenever `enable_3d` is off): a
  tall section after the hero with a sticky stage. Scroll position (0..1, CSS `--p`) turns the
  template's 3D model, moves the camera, tilts orbit rings and spins a particle shell while the
  business's first 2–3 services step through one at a time with a progress rail. It reuses the
  hero's lazy three.js chunk and the same gate (hardware WebGL, idle, in view); without WebGL the
  hero art turns in CSS, and with reduced motion the section is a plain list.
- **Card tilt**: on fine pointers, `.card`s tilt toward the cursor with a moving glare (the
  independent `rotate` property, so it composes with reveal and hover transforms).

### Guardrails

- The hero fallback image is server-rendered, `loading="eager"`, `fetchpriority="high"` and
  preloaded — it is the LCP element and stays visible under the 3D layer.
- `prefers-reduced-motion`: no Lenis, no GSAP scrubs/pins, no reveal animations, no 3D, no video
  (poster only).
- No WebGL, or a **software** WebGL renderer (SwiftShader/llvmpipe — headless CI, VMs, blocklisted
  GPUs), Save-Data, or `deviceMemory < 2` → fallback image, three.js never downloaded. Append
  `?force3d` to the URL to allow software rendering (used for screenshots).
- `hero.enable_3d: false` → the 3D component is not rendered and three.js is never requested.
- `hero.video` → muted, looping, `playsinline` `<video>` (webm + mp4, poster) mounted after
  hydration; reduced motion / Save-Data get the poster only. Video replaces the 3D layer.
- Without JavaScript, all content is visible (a `<noscript>` style cancels entrance states).

## Budgets

- **First-load JS for `/` ≤ 250 KB gzipped** (`npm run check:budget`): sums every script that
  `out/index.html` references (`<script src>` + `<link rel=preload as=script>`), gzip -9. Next's
  `<script nomodule>` legacy polyfills are reported but not counted (modern browsers never
  download them). The check also fails if three.js / R3F code appears in any first-load chunk.
  Current: **≈ 191 KB** for every template (React + Next runtime ≈ 115 KB of that).
- Lighthouse CI (`templates/lighthouserc.json`, mobile, simulated throttling): performance ≥ 0.9,
  accessibility ≥ 0.9. Run from `templates/`: `npx @lhci/cli autorun`. SEO is not asserted
  because preview builds are intentionally `noindex`.
- No layout shift: every image has explicit `width`/`height` and a fixed aspect ratio; fonts are
  preloaded and use `font-display: swap`.

## Accessibility

WCAG 2.2 AA target: skip link, landmarks (`header`/`nav`/`main`/`footer`, labelled sections),
`lang` from `locale`, visible focus rings, ≥ 44px tap targets, accessible form errors and status
messages, `aria-current="date"` on today's hours row. Text colours are derived from the theme with
contrast checks (`src/lib/color.ts`): body text ≥ 7:1, muted text and links ≥ 4.5:1, and button
labels pick black/white for ≥ 4.5:1 on `theme.primary`.
