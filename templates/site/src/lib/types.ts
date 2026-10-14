// TypeScript mirror of api/leadforge/schemas/site_spec.py (contract: ../site-spec.schema.json).
// Keep in sync with the Pydantic model; `normalizeSpec` fills the Pydantic defaults.

export const TEMPLATE_IDS = [
  "restaurant",
  "clinic",
  "salon",
  "fitness",
  "legal-finance",
  "real-estate",
  "home-services",
  "generic-premium",
] as const;
export type TemplateId = (typeof TEMPLATE_IDS)[number];

export const HERO_MODELS = ["tooth", "plate", "droplet", "dumbbell", "pillar", "house", "wrench", "orb"] as const;
export type HeroModel = (typeof HERO_MODELS)[number];

export const SECTION_TYPES = [
  "services",
  "about",
  "social_proof",
  "gallery",
  "hours",
  "map",
  "faq",
  "pricing",
  "contact",
] as const;
export type SectionType = (typeof SECTION_TYPES)[number];

export const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"] as const;
export type Day = (typeof DAYS)[number];

export interface Address {
  street: string;
  city: string;
  state?: string | null;
  postal_code?: string | null;
  country: "IN" | "US";
}

export interface HoursRow {
  day: Day;
  opens: string;
  closes: string;
}

export interface Social {
  platform: string;
  url: string;
}

export interface BusinessInfo {
  name: string;
  category: string;
  tagline: string;
  description: string;
  phone_e164: string | null;
  phone_display: string | null;
  whatsapp_e164: string | null;
  email: string | null;
  address: Address;
  lat: number | null;
  lng: number | null;
  google_maps_url: string | null;
  hours: HoursRow[];
  rating: number | null;
  review_count: number | null;
  socials: Social[];
}

export interface Seo {
  title: string;
  description: string;
  primary_keyword: string;
  keywords: string[];
}

export interface Theme {
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  foreground: string;
  mode: "light" | "dark";
  font_heading: string;
  font_body: string;
  radius_px: number;
}

export interface Link {
  label: string;
  href: string;
}

export interface ImageAsset {
  src: string;
  alt: string;
  credit: string | null;
  credit_url: string | null;
}

export interface VideoAsset {
  webm: string;
  mp4: string;
  poster: string;
}

export interface Hero {
  headline: string;
  subheadline: string;
  cta_primary: Link;
  cta_secondary: Link | null;
  model: HeroModel;
  enable_3d: boolean;
  scroll_scene: boolean;
  video: VideoAsset | null;
  fallback_image: ImageAsset;
}

export interface Service {
  title: string;
  description: string;
  icon: string;
  price: string | null;
}

export interface About {
  heading: string;
  body: string;
}

export interface Testimonial {
  quote: string;
  author: string;
  source: string;
  source_url: string | null;
}

export interface SocialProof {
  rating: number | null;
  review_count: number | null;
  source: string;
  source_url: string | null;
  testimonials: Testimonial[];
}

export interface Faq {
  q: string;
  a: string;
}

export interface PricingTier {
  name: string;
  price: string;
  features: string[];
}

export interface Contact {
  form_endpoint: string;
  site_id: string;
  turnstile_site_key: string | null;
  booking_url: string | null;
}

export interface Analytics {
  enabled: boolean;
  provider: "plausible" | "ga4" | null;
  id: string | null;
}

/** An inner page mirroring a page of the business's current site (page parity). */
export interface Page {
  path: string; // "/services/teeth-whitening", no trailing slash
  kind: string;
  nav_label: string;
  in_nav: boolean;
  parent: string | null;
  title: string;
  description: string;
  heading: string;
  intro: string;
  sections: SectionType[];
  placeholders: string[];
  source_path: string | null;
}

export interface Redirect {
  from_path: string;
  to_path: string;
}

export interface SiteSpec {
  spec_version: string;
  template: TemplateId;
  locale: "en-IN" | "en-US";
  currency: "INR" | "USD";
  site_url: string;
  noindex: boolean;
  business: BusinessInfo;
  seo: Seo;
  theme: Theme;
  hero: Hero;
  sections: SectionType[];
  services: Service[];
  about: About | null;
  social_proof: SocialProof;
  gallery: ImageAsset[];
  faq: Faq[];
  pricing: PricingTier[];
  contact: Contact;
  analytics: Analytics;
  pages: Page[];
  redirects: Redirect[];
  placeholders: string[];
  attribution: string[];
}
