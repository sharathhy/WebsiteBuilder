import type { HeroModel, TemplateId } from "./types";

/**
 * A template is a preset inside the one site project: layout feel, card style, motion
 * personality and default 3D model. Colours always come from `spec.theme`.
 */
export type HeroLayout = "fullbleed" | "split" | "arch" | "poster" | "stage";
export type CardStyle = "glass" | "outline" | "solid" | "elevated";
export type ServicesVariant = "cards" | "menu" | "numbered";

export interface MotionPersonality {
  /** seconds */
  duration: number;
  /** px travelled by entrance transitions */
  distance: number;
  stagger: number;
  ease: [number, number, number, number];
  /** hover lift in px */
  lift: number;
  /** multiplier for parallax layers */
  parallax: number;
}

export interface TemplatePreset {
  id: TemplateId;
  label: string;
  heroLayout: HeroLayout;
  cardStyle: CardStyle;
  servicesVariant: ServicesVariant;
  defaultModel: HeroModel;
  /** eyebrow labels for section headings */
  eyebrows: Partial<Record<string, string>>;
  /** fallback font stacks when the spec's font is not bundled */
  headingStack: string;
  bodyStack: string;
  motion: MotionPersonality;
  /** schema.org type for the LocalBusiness JSON-LD (refined by category in jsonld.ts) */
  schemaType: string;
}

const SANS = 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
const SERIF = 'ui-serif, Georgia, Cambria, "Times New Roman", Times, serif';
const CONDENSED = '"Arial Narrow", "Roboto Condensed", Impact, ui-sans-serif, system-ui, sans-serif';

const easeOut: [number, number, number, number] = [0.22, 1, 0.36, 1];
const easeSnap: [number, number, number, number] = [0.16, 1, 0.3, 1];
const easeSoft: [number, number, number, number] = [0.33, 1, 0.68, 1];

export const PRESETS: Record<TemplateId, TemplatePreset> = {
  restaurant: {
    id: "restaurant",
    label: "Restaurant",
    heroLayout: "fullbleed",
    cardStyle: "glass",
    servicesVariant: "menu",
    defaultModel: "plate",
    eyebrows: { services: "The menu", about: "Our story", gallery: "At the table", hours: "Kitchen hours", faq: "Good to know", contact: "Reservations" },
    headingStack: SERIF,
    bodyStack: SANS,
    motion: { duration: 1.1, distance: 36, stagger: 0.12, ease: easeSoft, lift: 4, parallax: 1.2 },
    schemaType: "Restaurant",
  },
  clinic: {
    id: "clinic",
    label: "Clinic",
    heroLayout: "split",
    cardStyle: "elevated",
    servicesVariant: "cards",
    defaultModel: "tooth",
    eyebrows: { services: "Treatments", about: "About the practice", gallery: "Inside the clinic", hours: "Clinic hours", faq: "Patient questions", contact: "Book a visit" },
    headingStack: SANS,
    bodyStack: SANS,
    motion: { duration: 0.7, distance: 20, stagger: 0.07, ease: easeOut, lift: 4, parallax: 0.6 },
    schemaType: "MedicalClinic",
  },
  salon: {
    id: "salon",
    label: "Salon & spa",
    heroLayout: "arch",
    cardStyle: "glass",
    servicesVariant: "numbered",
    defaultModel: "droplet",
    eyebrows: { services: "Rituals", about: "The studio", gallery: "Lookbook", hours: "Studio hours", faq: "Before you visit", contact: "Reserve a chair" },
    headingStack: SERIF,
    bodyStack: SANS,
    motion: { duration: 1.2, distance: 28, stagger: 0.1, ease: easeSoft, lift: 6, parallax: 1 },
    schemaType: "BeautySalon",
  },
  fitness: {
    id: "fitness",
    label: "Fitness",
    heroLayout: "poster",
    cardStyle: "solid",
    servicesVariant: "numbered",
    defaultModel: "dumbbell",
    eyebrows: { services: "Train", about: "The gym", gallery: "The floor", hours: "Open hours", faq: "FAQ", pricing: "Memberships", contact: "Start today" },
    headingStack: CONDENSED,
    bodyStack: SANS,
    motion: { duration: 0.55, distance: 48, stagger: 0.06, ease: easeSnap, lift: 8, parallax: 1.4 },
    schemaType: "HealthClub",
  },
  "legal-finance": {
    id: "legal-finance",
    label: "Legal & finance",
    heroLayout: "split",
    cardStyle: "outline",
    servicesVariant: "numbered",
    defaultModel: "pillar",
    eyebrows: { services: "Practice areas", about: "The firm", gallery: "Office", hours: "Office hours", faq: "Common questions", contact: "Consultation" },
    headingStack: SERIF,
    bodyStack: SANS,
    motion: { duration: 0.8, distance: 14, stagger: 0.06, ease: easeOut, lift: 2, parallax: 0.4 },
    schemaType: "LegalService",
  },
  "real-estate": {
    id: "real-estate",
    label: "Real estate",
    heroLayout: "fullbleed",
    cardStyle: "glass",
    servicesVariant: "cards",
    defaultModel: "house",
    eyebrows: { services: "What we do", about: "About us", gallery: "Featured spaces", hours: "Office hours", faq: "Buyer & seller FAQ", contact: "Talk to an agent" },
    headingStack: SANS,
    bodyStack: SANS,
    motion: { duration: 0.9, distance: 24, stagger: 0.08, ease: easeOut, lift: 5, parallax: 1 },
    schemaType: "RealEstateAgent",
  },
  "home-services": {
    id: "home-services",
    label: "Home services",
    heroLayout: "split",
    cardStyle: "solid",
    servicesVariant: "cards",
    defaultModel: "wrench",
    eyebrows: { services: "Services", about: "Why us", gallery: "Recent work", hours: "Working hours", faq: "Questions", pricing: "Pricing", contact: "Get a quote" },
    headingStack: SANS,
    bodyStack: SANS,
    motion: { duration: 0.5, distance: 18, stagger: 0.05, ease: easeSnap, lift: 4, parallax: 0.5 },
    schemaType: "HomeAndConstructionBusiness",
  },
  "generic-premium": {
    id: "generic-premium",
    label: "Premium",
    heroLayout: "stage",
    cardStyle: "glass",
    servicesVariant: "cards",
    defaultModel: "orb",
    eyebrows: { services: "Services", about: "About", gallery: "Gallery", hours: "Hours", faq: "FAQ", contact: "Contact" },
    headingStack: SANS,
    bodyStack: SANS,
    motion: { duration: 0.9, distance: 28, stagger: 0.08, ease: easeOut, lift: 6, parallax: 1 },
    schemaType: "LocalBusiness",
  },
};

export function getPreset(id: TemplateId): TemplatePreset {
  return PRESETS[id] ?? PRESETS["generic-premium"];
}
