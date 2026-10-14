import { getPreset } from "./presets";
import { HERO_MODELS, SECTION_TYPES, TEMPLATE_IDS, type SiteSpec } from "./types";

/* eslint-disable @typescript-eslint/no-explicit-any */

const str = (v: unknown): string | null => (typeof v === "string" && v.trim() !== "" ? v : null);
const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);
const arr = <T>(v: unknown): T[] => (Array.isArray(v) ? (v as T[]) : []);

function image(raw: any) {
  return {
    src: String(raw?.src ?? ""),
    alt: String(raw?.alt ?? ""),
    credit: str(raw?.credit),
    credit_url: str(raw?.credit_url),
  };
}

/**
 * Apply the Pydantic defaults to a raw spec (as produced by `model_dump(mode="json")` or a
 * hand-written file that omits defaulted fields). Structural validation against the JSON
 * Schema happens in scripts/prepare-spec.mjs before the build starts.
 */
export function normalizeSpec(raw: any): SiteSpec {
  if (!raw || typeof raw !== "object") throw new Error("Site spec must be a JSON object");
  const template = TEMPLATE_IDS.includes(raw.template) ? raw.template : "generic-premium";
  const preset = getPreset(template);
  const b = raw.business ?? {};
  const t = raw.theme ?? {};
  const h = raw.hero ?? {};
  const sp = raw.social_proof ?? {};
  const c = raw.contact ?? {};
  const an = raw.analytics ?? {};

  const model = HERO_MODELS.includes(h.model) ? h.model : preset.defaultModel;

  const seen = new Set<string>();
  const sections = arr<string>(raw.sections).filter((s) => {
    if (!SECTION_TYPES.includes(s as never) || seen.has(s)) return false;
    seen.add(s);
    return true;
  }) as SiteSpec["sections"];

  return {
    spec_version: str(raw.spec_version) ?? "1.0",
    template,
    locale: raw.locale === "en-US" ? "en-US" : "en-IN",
    currency: raw.currency === "USD" ? "USD" : "INR",
    site_url: String(raw.site_url ?? "https://example.com").replace(/\/+$/, ""),
    noindex: raw.noindex !== false,
    business: {
      name: String(b.name ?? ""),
      category: String(b.category ?? ""),
      tagline: String(b.tagline ?? ""),
      description: String(b.description ?? ""),
      phone_e164: str(b.phone_e164),
      phone_display: str(b.phone_display),
      whatsapp_e164: str(b.whatsapp_e164),
      email: str(b.email),
      address: {
        street: String(b.address?.street ?? ""),
        city: String(b.address?.city ?? ""),
        state: str(b.address?.state),
        postal_code: str(b.address?.postal_code),
        country: b.address?.country === "US" ? "US" : "IN",
      },
      lat: num(b.lat),
      lng: num(b.lng),
      google_maps_url: str(b.google_maps_url),
      hours: arr<any>(b.hours).map((r) => ({ day: r.day, opens: r.opens, closes: r.closes })),
      rating: num(b.rating),
      review_count: num(b.review_count),
      socials: arr<any>(b.socials)
        .filter((s) => str(s?.url))
        .map((s) => ({ platform: String(s.platform ?? ""), url: String(s.url) })),
    },
    seo: {
      title: String(raw.seo?.title ?? b.name ?? ""),
      description: String(raw.seo?.description ?? b.description ?? ""),
      primary_keyword: String(raw.seo?.primary_keyword ?? ""),
      keywords: arr<string>(raw.seo?.keywords).map(String),
    },
    theme: {
      primary: t.primary ?? "#4f46e5",
      secondary: t.secondary ?? "#0ea5e9",
      accent: t.accent ?? "#f59e0b",
      background: t.background ?? "#ffffff",
      foreground: t.foreground ?? "#0f172a",
      mode: t.mode === "dark" ? "dark" : "light",
      font_heading: str(t.font_heading) ?? "Inter",
      font_body: str(t.font_body) ?? "Inter",
      radius_px: typeof t.radius_px === "number" ? Math.max(0, Math.min(40, t.radius_px)) : 16,
    },
    hero: {
      headline: String(h.headline ?? b.name ?? ""),
      subheadline: String(h.subheadline ?? ""),
      cta_primary: { label: String(h.cta_primary?.label ?? "Contact"), href: String(h.cta_primary?.href ?? "#contact") },
      cta_secondary: h.cta_secondary?.label
        ? { label: String(h.cta_secondary.label), href: String(h.cta_secondary.href ?? "#") }
        : null,
      model,
      enable_3d: h.enable_3d !== false,
      video:
        h.video && str(h.video.webm) && str(h.video.mp4) && str(h.video.poster)
          ? { webm: h.video.webm, mp4: h.video.mp4, poster: h.video.poster }
          : null,
      fallback_image: image(h.fallback_image),
    },
    sections,
    services: arr<any>(raw.services).map((s) => ({
      title: String(s.title ?? ""),
      description: String(s.description ?? ""),
      icon: str(s.icon) ?? "sparkles",
      price: str(s.price),
    })),
    about: raw.about && str(raw.about.heading) ? { heading: raw.about.heading, body: String(raw.about.body ?? "") } : null,
    social_proof: {
      rating: num(sp.rating),
      review_count: num(sp.review_count),
      source: str(sp.source) ?? "Google",
      source_url: str(sp.source_url),
      testimonials: arr<any>(sp.testimonials)
        .filter((x) => str(x?.quote) && str(x?.author))
        .map((x) => ({ quote: x.quote, author: x.author, source: String(x.source ?? ""), source_url: str(x.source_url) })),
    },
    gallery: arr<any>(raw.gallery).map(image).filter((g) => g.src),
    faq: arr<any>(raw.faq).filter((f) => str(f?.q)).map((f) => ({ q: String(f.q), a: String(f.a ?? "") })),
    pricing: arr<any>(raw.pricing).map((p) => ({
      name: String(p.name ?? ""),
      price: String(p.price ?? ""),
      features: arr<string>(p.features).map(String),
    })),
    contact: {
      form_endpoint: String(c.form_endpoint ?? ""),
      site_id: String(c.site_id ?? ""),
      turnstile_site_key: str(c.turnstile_site_key),
      booking_url: str(c.booking_url),
    },
    analytics: {
      enabled: an.enabled === true,
      provider: an.provider === "plausible" || an.provider === "ga4" ? an.provider : null,
      id: str(an.id),
    },
    pages: arr<any>(raw.pages)
      .filter((p) => typeof p?.path === "string" && /^\/[a-z0-9-]+(\/[a-z0-9-]+)*$/.test(p.path))
      .map((p) => ({
        path: p.path,
        kind: String(p.kind ?? "other"),
        nav_label: String(p.nav_label ?? p.heading ?? p.path),
        in_nav: p.in_nav !== false,
        parent: str(p.parent),
        title: String(p.title ?? p.heading ?? ""),
        description: String(p.description ?? ""),
        heading: String(p.heading ?? p.nav_label ?? ""),
        intro: String(p.intro ?? ""),
        sections: arr<string>(p.sections).filter((s) => SECTION_TYPES.includes(s as never)) as SiteSpec["sections"],
        placeholders: arr<string>(p.placeholders).map(String),
        source_path: str(p.source_path),
      })),
    redirects: arr<any>(raw.redirects)
      .filter((r) => str(r?.from_path) && str(r?.to_path))
      .map((r) => ({ from_path: String(r.from_path), to_path: String(r.to_path) })),
    placeholders: arr<string>(raw.placeholders).map(String).filter(Boolean),
    attribution: arr<string>(raw.attribution).map(String).filter(Boolean),
  };
}

/** Effective rating: social_proof overrides business when present. */
export function effectiveRating(spec: SiteSpec): { rating: number | null; count: number | null; url: string | null; source: string } {
  const rating = spec.social_proof.rating ?? spec.business.rating;
  const count = spec.social_proof.review_count ?? spec.business.review_count;
  return {
    rating,
    count,
    url: spec.social_proof.source_url ?? spec.business.google_maps_url,
    source: spec.social_proof.source || "Google",
  };
}
