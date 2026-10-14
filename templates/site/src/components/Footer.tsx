import { CalendarCheck, Phone } from "lucide-react";
import Link from "next/link";
import { addressLines, displayPhone, telHref, whatsappHref } from "@/lib/format";
import { SocialIcon, WhatsAppIcon } from "./brand-icons";
import type { SiteCtx } from "./common";

/** NAP footer: name, address and phone exactly as in the business record. */
export function Footer({ ctx }: { ctx: SiteCtx }) {
  const { spec } = ctx;
  const b = spec.business;
  const phone = displayPhone(spec);
  const year = new Date().getFullYear();
  return (
    <footer className="relative border-t border-line bg-surface" aria-labelledby="footer-title">
      <div className="container-x grid gap-10 py-16 md:grid-cols-[1.4fr_1fr_1fr] md:py-20">
        <div>
          <h2 id="footer-title" className="font-heading text-[length:var(--step-3)]">
            {b.name}
          </h2>
          <p className="mt-3 max-w-sm text-muted">{b.tagline}</p>
          {b.socials.length ? (
            <ul className="mt-6 flex flex-wrap gap-2" aria-label="Social media">
              {b.socials.map((s) => (
                <li key={s.url}>
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noopener noreferrer me"
                    className="grid size-11 place-items-center rounded-full border border-line hover:bg-fg/5"
                    aria-label={`${b.name} on ${s.platform}`}
                    data-track="social_click"
                  >
                    <SocialIcon platform={s.platform} size={18} />
                  </a>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-muted">Visit</h3>
          <address className="mt-4 not-italic leading-relaxed">
            {addressLines(b.address).map((l, i) => (
              <span key={i} className="block">
                {l}
              </span>
            ))}
          </address>
          {b.google_maps_url ? (
            <a href={b.google_maps_url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-flex min-h-11 items-center underline underline-offset-4">
              Directions
            </a>
          ) : null}
        </div>
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-muted">Contact</h3>
          <ul className="mt-4 grid gap-1">
            {b.phone_e164 ? (
              <li>
                <a href={telHref(b.phone_e164)} className="inline-flex min-h-11 items-center underline-offset-4 hover:underline" data-track="call_click" data-track-location="footer">
                  {phone}
                </a>
              </li>
            ) : null}
            {b.email ? (
              <li>
                <a href={`mailto:${b.email}`} className="inline-flex min-h-11 items-center break-all underline-offset-4 hover:underline">
                  {b.email}
                </a>
              </li>
            ) : null}
            <li>
              <Link href="/privacy/" prefetch={false} className="inline-flex min-h-11 items-center underline-offset-4 hover:underline">
                Privacy policy
              </Link>
            </li>
          </ul>
        </div>
      </div>
      {spec.pages.length ? (
        <nav aria-label="All pages" className="container-x border-t border-line py-8">
          <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-muted">Pages</h3>
          <ul className="mt-3 flex flex-wrap gap-x-6 gap-y-1">
            {spec.pages.map((p) => (
              <li key={p.path}>
                <Link href={`${p.path}/`} prefetch={false} className="inline-flex min-h-11 items-center underline-offset-4 hover:underline">
                  {p.nav_label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}
      <div className="border-t border-line">
        <div className="container-x flex flex-col gap-2 py-6 text-sm text-muted md:flex-row md:items-center md:justify-between">
          <p>
            © {year} {b.name}
          </p>
          {spec.attribution.length ? <p className="max-w-3xl">{spec.attribution.join(" · ")}</p> : null}
        </div>
      </div>
    </footer>
  );
}

/** Sticky bottom bar on mobile with only the actions present in the spec. */
export function MobileActionBar({ ctx }: { ctx: SiteCtx }) {
  const b = ctx.spec.business;
  const booking = ctx.spec.contact.booking_url;
  const actions = [
    b.phone_e164 && (
      <a key="call" href={telHref(b.phone_e164)} className="btn btn-primary flex-1" data-track="call_click" data-track-location="action_bar">
        <Phone size={18} aria-hidden="true" />
        Call
      </a>
    ),
    b.whatsapp_e164 && (
      <a
        key="wa"
        href={whatsappHref(b.whatsapp_e164, `Hi ${b.name}, I found you online.`)}
        target="_blank"
        rel="noopener noreferrer"
        className="btn flex-1 bg-[#0f7a3f] text-white"
        data-track="whatsapp_click"
        data-track-location="action_bar"
      >
        <WhatsAppIcon size={18} />
        WhatsApp
      </a>
    ),
    booking && (
      <a key="book" href={booking} target="_blank" rel="noopener noreferrer" className="btn btn-ghost flex-1" data-track="booking_click" data-track-location="action_bar">
        <CalendarCheck size={18} aria-hidden="true" />
        Book
      </a>
    ),
  ].filter(Boolean);
  if (!actions.length) return null;
  return (
    <nav aria-label="Quick actions" className="action-bar">
      <div className="mx-auto flex max-w-lg gap-2">{actions}</div>
    </nav>
  );
}
