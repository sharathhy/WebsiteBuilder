import type { Metadata } from "next";
import Link from "next/link";
import { SiteShell } from "@/components/SiteShell";
import { getSiteCtx } from "@/lib/site";

export const metadata: Metadata = { title: "Page not found" };

export default function NotFound() {
  const ctx = getSiteCtx();
  return (
    <SiteShell ctx={ctx} home={false}>
      <section className="container-x grid min-h-[60svh] place-items-center py-24 text-center" aria-labelledby="nf-title">
        <div>
          <p className="eyebrow justify-center">Error 404</p>
          <h1 id="nf-title" className="h-section">
            This page doesn&rsquo;t exist
          </h1>
          <p className="lede mx-auto mt-4">The link may be broken or the page may have moved.</p>
          <Link href="/" className="btn btn-primary mt-8">
            Go to {ctx.spec.business.name}
          </Link>
        </div>
      </section>
    </SiteShell>
  );
}
