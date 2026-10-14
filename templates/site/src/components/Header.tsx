import { Phone } from "lucide-react";
import Link from "next/link";
import { displayPhone, initials, telHref, withBase } from "@/lib/format";
import type { SiteCtx } from "./common";
import { MobileMenu } from "./MobileMenu";
import type { SectionType } from "@/lib/types";

export const SECTION_LABEL: Record<SectionType, string> = {
  services: "Services",
  about: "About",
  social_proof: "Reviews",
  gallery: "Gallery",
  hours: "Hours",
  map: "Location",
  faq: "FAQ",
  pricing: "Pricing",
  contact: "Contact",
};

export function Header({ ctx, sections, home = true }: { ctx: SiteCtx; sections: SectionType[]; home?: boolean }) {
  const { spec } = ctx;
  const prefix = home ? "" : withBase("/");
  const links = sections.map((s) => ({ href: `${prefix}#${s}`, label: SECTION_LABEL[s] }));
  const desktop = links.filter((l) => !/#(hours|map)$/.test(l.href)).slice(0, 5);
  const phone = displayPhone(spec);
  return (
    <header className="site-header">
      <div className="container-x relative flex h-16 items-center justify-between gap-4 md:h-[72px]">
        <Link href="/" prefetch={false} className="flex min-h-11 items-center gap-3 rounded-lg no-underline">
          <span
            aria-hidden="true"
            className="grid size-10 shrink-0 place-items-center rounded-[calc(var(--radius)*0.7)] bg-primary text-sm font-bold tracking-wide text-on-primary"
          >
            {initials(spec.business.name)}
          </span>
          <span className="max-w-[46vw] truncate font-heading text-lg font-semibold leading-tight sm:max-w-none">
            {spec.business.name}
          </span>
        </Link>
        <nav aria-label="Primary" className="hidden lg:block">
          <ul className="flex items-center gap-1">
            {desktop.map((l) => (
              <li key={l.href}>
                <a href={l.href} className="nav-link">
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <div className="flex items-center gap-2">
          {spec.business.phone_e164 ? (
            <a
              href={telHref(spec.business.phone_e164)}
              className="btn btn-primary hidden !min-h-11 !px-4 !text-[0.95rem] md:inline-flex"
              data-track="call_click"
              data-track-location="header"
            >
              <Phone size={17} aria-hidden="true" />
              <span>{phone}</span>
            </a>
          ) : null}
          {links.length ? <MobileMenu links={links} /> : null}
        </div>
      </div>
    </header>
  );
}
