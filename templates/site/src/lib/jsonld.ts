import { absoluteUrl, telHref } from "./format";
import { effectiveRating } from "./normalize";
import { getPreset } from "./presets";
import type { SiteSpec } from "./types";

/** Most specific schema.org type for the template, refined by the business category. */
export function schemaType(spec: SiteSpec): string {
  const cat = `${spec.business.category} ${spec.seo.primary_keyword}`.toLowerCase();
  switch (spec.template) {
    case "clinic":
      return /dent|orthodont|tooth|teeth/.test(cat) ? "Dentist" : "MedicalClinic";
    case "legal-finance":
      return /account|cpa|chartered|tax|audit|bookkeep|financ/.test(cat) ? "AccountingService" : "LegalService";
    case "restaurant":
      return /caf[eé]|coffee/.test(cat) ? "CafeOrCoffeeShop" : "Restaurant";
    case "salon":
      return /spa\b|day spa/.test(cat) && !/salon/.test(cat) ? "DaySpa" : "BeautySalon";
    default:
      return getPreset(spec.template).schemaType;
  }
}

function resolveImage(spec: SiteSpec, src: string): string {
  return /^https?:\/\//.test(src) ? src : absoluteUrl(spec, src);
}

export function buildLocalBusinessJsonLd(spec: SiteSpec): Record<string, unknown> {
  const b = spec.business;
  const url = absoluteUrl(spec, "/");
  const data: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": schemaType(spec),
    "@id": `${url}#business`,
    name: b.name,
    description: b.description,
    url,
    image: resolveImage(spec, spec.hero.fallback_image.src),
    address: {
      "@type": "PostalAddress",
      streetAddress: b.address.street,
      addressLocality: b.address.city,
      ...(b.address.state ? { addressRegion: b.address.state } : {}),
      ...(b.address.postal_code ? { postalCode: b.address.postal_code } : {}),
      addressCountry: b.address.country,
    },
  };
  if (b.phone_e164) data.telephone = telHref(b.phone_e164).slice(4);
  if (b.email) data.email = b.email;
  if (b.lat != null && b.lng != null) data.geo = { "@type": "GeoCoordinates", latitude: b.lat, longitude: b.lng };
  if (b.google_maps_url) data.hasMap = b.google_maps_url;
  if (b.hours.length) {
    data.openingHoursSpecification = b.hours.map((h) => ({
      "@type": "OpeningHoursSpecification",
      dayOfWeek: `https://schema.org/${h.day}`,
      opens: h.opens,
      closes: h.closes,
    }));
  }
  const r = effectiveRating(spec);
  if (r.rating != null && r.count != null && r.count > 0) {
    data.aggregateRating = {
      "@type": "AggregateRating",
      ratingValue: r.rating,
      reviewCount: r.count,
      bestRating: 5,
      worstRating: 1,
    };
  }
  if (b.socials.length) data.sameAs = b.socials.map((s) => s.url);
  if (spec.currency) data.currenciesAccepted = spec.currency;
  return data;
}

export function buildFaqJsonLd(spec: SiteSpec): Record<string, unknown> | null {
  if (!spec.sections.includes("faq") || spec.faq.length === 0) return null;
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: spec.faq.map((f) => ({
      "@type": "Question",
      name: f.q,
      acceptedAnswer: { "@type": "Answer", text: f.a },
    })),
  };
}

/** Serialise for a <script type="application/ld+json"> without allowing `</script>` breakout. */
export function jsonLdString(data: unknown): string {
  return JSON.stringify(data).replace(/</g, "\\u003c");
}
