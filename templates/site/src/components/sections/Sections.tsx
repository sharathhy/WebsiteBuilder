import { ArrowUpRight, CalendarCheck, Check, Mail, MapPin, Navigation, Phone, Plus, Quote } from "lucide-react";
import { WhatsAppIcon } from "../brand-icons";
import { Credit, Img, SectionHeading, Stars, TbcChip, type SiteCtx } from "../common";
import { Icon } from "../Icon";
import { Reveal, RevealGroup, RevealItem } from "../motion/Reveal";
import { ContactForm } from "./ContactForm";
import { HoursTable } from "./HoursTable";
import { MapEmbed } from "./MapEmbed";
import {
  addressLines,
  businessTimeZone,
  displayPhone,
  formatPrice,
  initials,
  paragraphs,
  telHref,
  whatsappHref,
} from "@/lib/format";
import { effectiveRating } from "@/lib/normalize";
import { luminance } from "@/lib/color";
import type { SectionType } from "@/lib/types";

type P = { ctx: SiteCtx; alt: boolean };

const sectionClass = (alt: boolean) => `section ${alt ? "section-alt" : ""}`;
const eyebrow = (ctx: SiteCtx, key: string, fallback: string) => ctx.preset.eyebrows[key] ?? fallback;

/* ------------------------------------------------------------------ services */

function Services({ ctx, alt }: P) {
  const { spec, preset } = ctx;
  if (!spec.services.length) return null;
  const price = (p: string | null) => (p ? formatPrice(p, spec.locale, spec.currency) : null);
  const variant = preset.servicesVariant;
  const count = spec.services.length;

  const items = spec.services.map((s, i) => {
    if (variant === "menu") {
      return (
        <div key={i} data-depth>
          <RevealItem className="menu-row">
            <h3 className="flex items-baseline gap-3 text-[length:var(--step-2)]">
              <span>{s.title}</span>
              {price(s.price) ? <span className="leader" aria-hidden="true" /> : null}
            </h3>
            {price(s.price) ? (
              <p className="font-heading text-[length:var(--step-1)] text-primary-text tabular-nums">{price(s.price)}</p>
            ) : (
              <span />
            )}
            <p className="col-span-2 max-w-[60ch] text-muted">{s.description}</p>
          </RevealItem>
        </div>
      );
    }
    if (variant === "numbered") {
      return (
        <div key={i} data-depth>
          <RevealItem hover className="card grid grid-cols-[auto_1fr] gap-x-5 gap-y-2">
            <span className="font-heading text-[length:var(--step-3)] leading-none text-primary-text tabular-nums" aria-hidden="true">
              {String(i + 1).padStart(2, "0")}
            </span>
            <div>
              <h3 className="text-[length:var(--step-2)]">{s.title}</h3>
              <p className="mt-2 text-muted">{s.description}</p>
              {price(s.price) ? <p className="chip mt-4">{price(s.price)}</p> : null}
            </div>
          </RevealItem>
        </div>
      );
    }
    return (
      <div key={i} data-depth>
        <RevealItem hover className="card flex flex-col">
          <span className="icon-chip" aria-hidden="true">
            <Icon name={s.icon} />
          </span>
          <h3 className="mt-5 text-[length:var(--step-2)]">{s.title}</h3>
          <p className="mt-2 flex-1 text-muted">{s.description}</p>
          {price(s.price) ? <p className="chip mt-5 self-start">{price(s.price)}</p> : null}
        </RevealItem>
      </div>
    );
  });

  return (
    <section id="services" aria-labelledby="services-title" className={sectionClass(alt)} data-story>
      <div className="container-x grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
        <div data-pin className="lg:self-start">
          <SectionHeading id="services-title" eyebrow={eyebrow(ctx, "services", "Services")} title={spec.business.tagline || "What we offer"} lede={spec.business.description} />
          <div className="mt-8 hidden items-center gap-4 lg:flex" aria-hidden="true">
            <span className="progress-rail h-24">
              <span data-progress />
            </span>
            <span className="font-heading text-sm uppercase tracking-[0.2em] text-muted">
              {count} {count === 1 ? "service" : "services"}
            </span>
          </div>
        </div>
        <div data-story-list>
        <RevealGroup
          className={
            variant === "cards"
              ? "grid gap-4 [perspective:1200px] sm:grid-cols-2 md:gap-5"
              : variant === "menu"
                ? "grid [perspective:1200px]"
                : "grid gap-4 [perspective:1200px]"
          }
        >
          {items}
        </RevealGroup>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ about */

function About({ ctx, alt }: P) {
  const { spec } = ctx;
  if (!spec.about) return null;
  const b = spec.business;
  return (
    <section id="about" aria-labelledby="about-title" className={`${sectionClass(alt)} overflow-hidden`}>
      <div className="container-x grid items-center gap-12 md:grid-cols-[1.1fr_0.9fr] md:gap-16">
        <div>
          <SectionHeading id="about-title" eyebrow={eyebrow(ctx, "about", "About")} title={spec.about.heading} />
          <Reveal className="mt-6 grid gap-4 text-[length:var(--step-1)] leading-relaxed text-fg/85" delay={0.1}>
            {paragraphs(spec.about.body).map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </Reveal>
        </div>
        <Reveal className="relative mx-auto w-full max-w-md" delay={0.15}>
          <div className="glow inset-8 bg-primary opacity-40" data-speed="0.5" aria-hidden="true" />
          <div className="card relative overflow-hidden !p-8 md:!p-10" data-speed="0.15">
            <span
              aria-hidden="true"
              className="block font-heading text-[clamp(4rem,12vw,8rem)] font-bold leading-none tracking-tight text-primary-text/90"
            >
              {initials(b.name)}
            </span>
            <p className="mt-6 font-heading text-[length:var(--step-2)] leading-snug">{b.name}</p>
            <p className="mt-1 text-muted">{b.category}</p>
            <ul className="mt-6 grid gap-2 text-sm">
              <li className="flex items-start gap-2">
                <MapPin size={16} className="mt-0.5 shrink-0 text-primary-text" aria-hidden="true" />
                <span>{addressLines(b.address).slice(0, 2).join(", ")}</span>
              </li>
              {b.hours.length ? (
                <li className="flex items-start gap-2">
                  <CalendarCheck size={16} className="mt-0.5 shrink-0 text-primary-text" aria-hidden="true" />
                  <span>Open {new Set(b.hours.map((h) => h.day)).size} days a week</span>
                </li>
              ) : null}
            </ul>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ social proof */

function SocialProof({ ctx, alt }: P) {
  const { spec } = ctx;
  const r = effectiveRating(spec);
  const hasRating = r.rating != null && r.count != null && r.count > 0;
  const t = spec.social_proof.testimonials;
  if (!hasRating && t.length === 0) return null; // never show invented reviews
  return (
    <section id="social_proof" aria-labelledby="social_proof-title" className={sectionClass(alt)}>
      <div className="container-x">
        <SectionHeading id="social_proof-title" eyebrow="Reviews" title={hasRating ? `Rated ${r.rating!.toFixed(1)} on ${r.source}` : "What clients say"} />
        {hasRating ? (
          <Reveal className="card mt-10 flex flex-col items-start gap-6 md:flex-row md:items-center md:justify-between" delay={0.1}>
            <div className="flex items-center gap-5">
              <span className="font-heading text-[clamp(3.5rem,8vw,5.5rem)] font-semibold leading-none tabular-nums">
                {r.rating!.toFixed(1)}
              </span>
              <div>
                <Stars rating={r.rating!} size={22} />
                <p className="mt-2 text-muted">
                  Based on {r.count!.toLocaleString(spec.locale)} {r.source} reviews
                </p>
              </div>
            </div>
            {r.url ? (
              <a href={r.url} target="_blank" rel="noopener noreferrer" className="btn btn-ghost" data-track="reviews_click">
                Read reviews on {r.source}
                <ArrowUpRight size={18} aria-hidden="true" />
              </a>
            ) : null}
          </Reveal>
        ) : null}
        {t.length ? (
          <RevealGroup className="mt-6 grid gap-5 md:grid-cols-2 lg:grid-cols-3" as="ul">
            {t.map((x, i) => (
              <RevealItem key={i} as="li" hover className="card">
                <figure className="flex h-full flex-col">
                  <Quote size={28} className="text-primary-text" aria-hidden="true" />
                  <blockquote className="mt-4 flex-1 text-[length:var(--step-1)] leading-relaxed">
                    <p>{x.quote}</p>
                  </blockquote>
                  <figcaption className="mt-6 text-sm">
                    <span className="font-semibold">{x.author}</span>
                    <span className="text-muted">
                      {" "}
                      ·{" "}
                      {x.source_url ? (
                        <a href={x.source_url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
                          {x.source}
                        </a>
                      ) : (
                        x.source
                      )}
                    </span>
                  </figcaption>
                </figure>
              </RevealItem>
            ))}
          </RevealGroup>
        ) : null}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ gallery */

function Gallery({ ctx, alt }: P) {
  const { spec } = ctx;
  if (!spec.gallery.length) return null;
  return (
    <section id="gallery" aria-labelledby="gallery-title" className={`${sectionClass(alt)} overflow-hidden`}>
      <div className="container-x">
        <SectionHeading id="gallery-title" eyebrow={eyebrow(ctx, "gallery", "Gallery")} title={`Inside ${spec.business.name}`} />
        <RevealGroup className="mt-10 grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-5" as="ul">
          {spec.gallery.map((g, i) => {
            const big = i === 0 && spec.gallery.length >= 3 && spec.gallery.length % 2 === 1;
            return (
              <RevealItem key={i} as="li" className={big ? "col-span-2 row-span-2" : ""}>
                <figure className="group h-full">
                  <div
                    className="overflow-hidden rounded-[var(--radius)] bg-surface-2"
                    data-speed={big ? undefined : i % 2 ? "0.25" : "-0.15"}
                  >
                    <Img
                      image={g}
                      width={1200}
                      height={big ? 1200 : 900}
                      sizes={big ? "(min-width: 768px) 50vw, 100vw" : "(min-width: 768px) 25vw, 50vw"}
                      className={`w-full object-cover transition-transform duration-700 group-hover:scale-[1.04] ${big ? "aspect-square" : "aspect-[4/3]"}`}
                    />
                  </div>
                  {g.credit ? (
                    <figcaption className="mt-2 text-muted">
                      <Credit image={g} />
                    </figcaption>
                  ) : null}
                </figure>
              </RevealItem>
            );
          })}
        </RevealGroup>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ hours */

function Hours({ ctx, alt }: P) {
  const { spec } = ctx;
  if (!spec.business.hours.length) return null;
  const tz = businessTimeZone(spec.business.address);
  return (
    <section id="hours" aria-labelledby="hours-title" className={sectionClass(alt)}>
      <div className="container-x grid gap-10 md:grid-cols-[0.9fr_1.1fr] md:gap-16">
        <SectionHeading
          id="hours-title"
          eyebrow={eyebrow(ctx, "hours", "Hours")}
          title="When to find us"
          lede={<p>Times are local to {spec.business.address.city}.</p>}
        />
        <Reveal delay={0.1}>
          <HoursTable rows={spec.business.hours} locale={spec.locale} timeZone={tz} />
        </Reveal>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ map */

function MapSection({ ctx, alt }: P) {
  const { spec } = ctx;
  const b = spec.business;
  const hasGeo = b.lat != null && b.lng != null;
  if (!hasGeo && !b.google_maps_url) return null;
  return (
    <section id="map" aria-labelledby="map-title" className={sectionClass(alt)}>
      <div className="container-x grid items-center gap-10 md:grid-cols-[0.8fr_1.2fr] md:gap-16">
        <div>
          <SectionHeading id="map-title" eyebrow="Location" title={`Visit us in ${b.address.city}`} />
          <Reveal delay={0.1}>
            <address className="mt-6 not-italic text-[length:var(--step-1)] leading-relaxed">
              {addressLines(b.address).map((l, i) => (
                <span key={i} className="block">
                  {l}
                </span>
              ))}
            </address>
            {b.google_maps_url ? (
              <a href={b.google_maps_url} target="_blank" rel="noopener noreferrer" className="btn btn-ghost mt-6" data-track="directions_click">
                <Navigation size={18} aria-hidden="true" />
                Get directions
              </a>
            ) : null}
          </Reveal>
        </div>
        <Reveal delay={0.15}>
          {hasGeo ? (
            <MapEmbed lat={b.lat!} lng={b.lng!} title={`Map showing ${b.name}, ${b.address.city}`} mapsUrl={b.google_maps_url} />
          ) : null}
        </Reveal>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ faq */

function Faq({ ctx, alt }: P) {
  const { spec } = ctx;
  if (!spec.faq.length) return null;
  return (
    <section id="faq" aria-labelledby="faq-title" className={sectionClass(alt)}>
      <div className="container-x grid gap-10 md:grid-cols-[0.8fr_1.2fr] md:gap-16">
        <SectionHeading id="faq-title" eyebrow={eyebrow(ctx, "faq", "FAQ")} title="Questions, answered" />
        <RevealGroup className="border-t border-line">
          {spec.faq.map((f, i) => (
            <RevealItem key={i}>
              <details className="faq-item border-b border-line" name="faq">
                <summary>
                  <span>{f.q}</span>
                  <Plus className="faq-icon text-primary-text" size={22} aria-hidden="true" />
                </summary>
                <div className="pb-6 pr-8 text-muted">
                  {paragraphs(f.a).map((p, j) => (
                    <p key={j} className="mt-2 first:mt-0">
                      {p}
                    </p>
                  ))}
                </div>
              </details>
            </RevealItem>
          ))}
        </RevealGroup>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ pricing */

function Pricing({ ctx, alt }: P) {
  const { spec } = ctx;
  if (!spec.pricing.length) return null;
  return (
    <section id="pricing" aria-labelledby="pricing-title" className={sectionClass(alt)}>
      <div className="container-x">
        <SectionHeading id="pricing-title" eyebrow={eyebrow(ctx, "pricing", "Pricing")} title="Simple, published pricing" align="center" />
        <RevealGroup
          as="ul"
          className={`mx-auto mt-12 grid gap-5 ${spec.pricing.length >= 3 ? "md:grid-cols-3" : spec.pricing.length === 2 ? "max-w-4xl md:grid-cols-2" : "max-w-md"}`}
        >
          {spec.pricing.map((p, i) => (
            <RevealItem key={i} as="li" hover className="card flex flex-col">
              <h3 className="text-[length:var(--step-1)]">{p.name}</h3>
              <p className="mt-4 font-heading text-[length:var(--step-4)] font-semibold leading-none tabular-nums">
                {p.price ? formatPrice(p.price, spec.locale, spec.currency) : <TbcChip />}
              </p>
              {p.features.length ? (
                <ul className="mt-6 grid gap-3 text-[0.97rem]">
                  {p.features.map((f, j) => (
                    <li key={j} className="flex items-start gap-2.5">
                      <Check size={18} className="mt-0.5 shrink-0 text-primary-text" aria-hidden="true" />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
              <a href="#contact" className="btn btn-ghost mt-8 w-full">
                Enquire
              </a>
            </RevealItem>
          ))}
        </RevealGroup>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ contact */

function Contact({ ctx, alt }: P) {
  const { spec, tokens } = ctx;
  const b = spec.business;
  const phone = displayPhone(spec);
  return (
    <section id="contact" aria-labelledby="contact-title" className={`${sectionClass(alt)} overflow-hidden`}>
      <div className="glow -left-32 bottom-0 size-96 bg-primary opacity-25" aria-hidden="true" data-speed="0.4" />
      <div className="container-x grid gap-12 md:grid-cols-[0.85fr_1.15fr] md:gap-16">
        <div>
          <SectionHeading
            id="contact-title"
            eyebrow={eyebrow(ctx, "contact", "Contact")}
            title="Get in touch"
            lede={<p>Send a message and we&rsquo;ll reply as soon as we can{phone ? ", or call us directly" : ""}.</p>}
          />
          <Reveal className="mt-8 grid gap-3" delay={0.1}>
            {b.phone_e164 ? (
              <a href={telHref(b.phone_e164)} className="group flex min-h-11 items-center gap-3 no-underline" data-track="call_click" data-track-location="contact">
                <span className="icon-chip !size-11 shrink-0" aria-hidden="true">
                  <Phone size={18} />
                </span>
                <span>
                  <span className="block text-sm text-muted">Call</span>
                  <span className="font-semibold group-hover:underline">{phone}</span>
                </span>
              </a>
            ) : null}
            {b.whatsapp_e164 ? (
              <a
                href={whatsappHref(b.whatsapp_e164, `Hi ${b.name}, I found you online.`)}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex min-h-11 items-center gap-3 no-underline"
                data-track="whatsapp_click"
                data-track-location="contact"
              >
                <span className="icon-chip !size-11 shrink-0" aria-hidden="true">
                  <WhatsAppIcon size={18} />
                </span>
                <span>
                  <span className="block text-sm text-muted">WhatsApp</span>
                  <span className="font-semibold group-hover:underline">Message us</span>
                </span>
              </a>
            ) : null}
            {b.email ? (
              <a href={`mailto:${b.email}`} className="group flex min-h-11 items-center gap-3 no-underline" data-track="email_click">
                <span className="icon-chip !size-11 shrink-0" aria-hidden="true">
                  <Mail size={18} />
                </span>
                <span>
                  <span className="block text-sm text-muted">Email</span>
                  <span className="break-all font-semibold group-hover:underline">{b.email}</span>
                </span>
              </a>
            ) : null}
            <div className="flex min-h-11 items-center gap-3">
              <span className="icon-chip !size-11 shrink-0" aria-hidden="true">
                <MapPin size={18} />
              </span>
              <span>
                <span className="block text-sm text-muted">Address</span>
                <span className="font-semibold">{addressLines(b.address).slice(0, 2).join(", ")}</span>
              </span>
            </div>
            {spec.contact.booking_url ? (
              <a
                href={spec.contact.booking_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary mt-4 justify-self-start"
                data-track="booking_click"
                data-track-location="contact"
              >
                <CalendarCheck size={18} aria-hidden="true" />
                Book an appointment
              </a>
            ) : null}
          </Reveal>
        </div>
        <Reveal className="card !p-6 md:!p-10" delay={0.15}>
          <h3 className="mb-6 text-[length:var(--step-2)]">Send a message</h3>
          {spec.contact.form_endpoint ? (
            <ContactForm
              endpoint={spec.contact.form_endpoint}
              siteId={spec.contact.site_id}
              turnstileSiteKey={spec.contact.turnstile_site_key}
              dark={luminance(tokens.bg) < 0.4}
            />
          ) : (
            <TbcChip>Contact form to be connected</TbcChip>
          )}
        </Reveal>
      </div>
    </section>
  );
}

const RENDERERS: Record<SectionType, (p: P) => React.ReactNode> = {
  services: Services,
  about: About,
  social_proof: SocialProof,
  gallery: Gallery,
  hours: Hours,
  map: MapSection,
  faq: Faq,
  pricing: Pricing,
  contact: Contact,
};

/** Which listed sections actually have content (used for nav + alternating backgrounds). */
export function renderableSections(ctx: SiteCtx, list?: SectionType[]): SectionType[] {
  const { spec } = ctx;
  const r = effectiveRating(spec);
  return (list ?? spec.sections).filter((s) => {
    switch (s) {
      case "services":
        return spec.services.length > 0;
      case "about":
        return !!spec.about;
      case "social_proof":
        return (r.rating != null && (r.count ?? 0) > 0) || spec.social_proof.testimonials.length > 0;
      case "gallery":
        return spec.gallery.length > 0;
      case "hours":
        return spec.business.hours.length > 0;
      case "map":
        return (spec.business.lat != null && spec.business.lng != null) || !!spec.business.google_maps_url;
      case "faq":
        return spec.faq.length > 0;
      case "pricing":
        return spec.pricing.length > 0;
      case "contact":
        return true;
    }
  });
}

export function Sections({ ctx, sections, offset = 0 }: { ctx: SiteCtx; sections: SectionType[]; offset?: number }) {
  return (
    <>
      {sections.map((s, i) => {
        const R = RENDERERS[s];
        return <R key={s} ctx={ctx} alt={(i + offset) % 2 === 1} />;
      })}
    </>
  );
}
