import type { Metadata } from "next";
import Link from "next/link";
import { SiteShell } from "@/components/SiteShell";
import { absoluteUrl, addressLines, displayPhone } from "@/lib/format";
import { getSiteCtx } from "@/lib/site";

export function generateMetadata(): Metadata {
  const { spec } = getSiteCtx();
  return {
    title: `Privacy policy — ${spec.business.name}`,
    description: `How ${spec.business.name} handles information submitted through this website.`,
    alternates: { canonical: absoluteUrl(spec, "/privacy/") },
  };
}

export default function Privacy() {
  const ctx = getSiteCtx();
  const { spec } = ctx;
  const b = spec.business;
  const a = spec.analytics;
  const contactBits = [b.email, displayPhone(spec)].filter(Boolean).join(" or ");
  return (
    <SiteShell ctx={ctx} home={false}>
      <article className="container-x max-w-3xl py-16 md:py-24" aria-labelledby="privacy-title">
        <p className="eyebrow">Legal</p>
        <h1 id="privacy-title" className="h-section">
          Privacy policy
        </h1>
        <div className="mt-8 grid gap-6 text-[length:var(--step-0)] leading-relaxed [&_h2]:mt-6 [&_h2]:text-[length:var(--step-2)]">
          <p>
            This website is operated by <strong>{b.name}</strong>, {addressLines(b.address).join(", ")}. This page explains
            what information the website collects and how it is used.
          </p>
          <h2>Contact form</h2>
          <p>
            When you send a message through the contact form we receive the name, email address, phone number and message you
            enter. We use these details only to reply to your enquiry. We do not sell your information or use it for unrelated
            marketing.
          </p>
          {spec.contact.turnstile_site_key ? (
            <>
              <h2>Spam protection</h2>
              <p>
                The form uses Cloudflare Turnstile to check that submissions come from a person. Cloudflare may process
                technical information about your browser for this purpose.
              </p>
            </>
          ) : null}
          <h2>Maps</h2>
          <p>
            The map on this site is provided by Google Maps and is only loaded when you choose to view it or scroll to it.
            Google&rsquo;s privacy policy applies to that content.
          </p>
          <h2>Analytics</h2>
          <p>
            {a.enabled && a.provider
              ? `We use ${a.provider === "plausible" ? "Plausible Analytics" : "Google Analytics 4"} to understand how visitors use this site, such as which pages are viewed and which buttons are clicked.`
              : "This website does not use analytics or advertising cookies."}
          </p>
          <h2>Contact</h2>
          <p>
            Questions about this policy or requests to delete your information can be sent to {b.name}
            {contactBits ? ` at ${contactBits}` : ""}.
          </p>
          <p>
            <Link href="/" className="underline underline-offset-4">
              Back to the home page
            </Link>
          </p>
        </div>
      </article>
    </SiteShell>
  );
}
