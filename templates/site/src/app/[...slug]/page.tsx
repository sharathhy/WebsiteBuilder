import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { SiteShell } from "@/components/SiteShell";
import { SectionHeading } from "@/components/common";
import { Reveal, RevealGroup, RevealItem } from "@/components/motion/Reveal";
import { renderableSections, Sections } from "@/components/sections/Sections";
import { absoluteUrl } from "@/lib/format";
import { getSiteCtx } from "@/lib/site";
import { getSpec } from "@/lib/spec";
import type { Page } from "@/lib/types";

/*
 * Inner pages: one per page of the business's current site (page parity). The spec lists
 * them; nothing else is generated. Copy is written from known facts, and whatever only the
 * owner can supply is shown as a clearly marked placeholder.
 */

export const dynamicParams = false;

type Params = { slug: string[] };

/** Static export refuses a dynamic route with no params, so a one-page site gets a stub
 * (it can't collide: page paths are [a-z0-9-]) that scripts/postbuild.mjs deletes. */
export const NO_PAGES = "__no-pages";

export function generateStaticParams(): Params[] {
  const pages = getSpec().pages.map((p) => ({ slug: p.path.slice(1).split("/") }));
  return pages.length ? pages : [{ slug: [NO_PAGES] }];
}

function findPage(slug: string[]): Page | undefined {
  const path = "/" + slug.map(decodeURIComponent).join("/");
  return getSpec().pages.find((p) => p.path === path);
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const page = findPage((await params).slug);
  if (!page) return {};
  const spec = getSpec();
  return {
    title: page.title,
    description: page.description,
    alternates: { canonical: absoluteUrl(spec, `${page.path}/`) },
    openGraph: { title: page.title, description: page.description, url: absoluteUrl(spec, `${page.path}/`) },
  };
}

export default async function InnerPage({ params }: { params: Promise<Params> }) {
  const page = findPage((await params).slug);
  if (!page) notFound();
  const ctx = getSiteCtx();
  const { spec } = ctx;
  const parent = page.parent ? spec.pages.find((p) => p.path === page.parent) : undefined;
  const children = spec.pages.filter((p) => p.parent === page.path);
  const sections = renderableSections(ctx, page.sections);
  return (
    <SiteShell ctx={ctx} home={false}>
      <section className="section" aria-labelledby="page-title">
        <div className="container-x">
          <nav aria-label="Breadcrumb" className="mb-6 text-sm text-muted">
            <ol className="flex flex-wrap items-center gap-2">
              <li>
                <Link href="/" prefetch={false} className="underline-offset-4 hover:underline">
                  Home
                </Link>
              </li>
              {parent ? (
                <li className="flex items-center gap-2">
                  <span aria-hidden="true">/</span>
                  <Link href={`${parent.path}/`} prefetch={false} className="underline-offset-4 hover:underline">
                    {parent.nav_label}
                  </Link>
                </li>
              ) : null}
              <li className="flex items-center gap-2" aria-current="page">
                <span aria-hidden="true">/</span>
                <span>{page.nav_label}</span>
              </li>
            </ol>
          </nav>
          <div className="max-w-3xl">
            <SectionHeading id="page-title" title={page.heading} lede={page.intro} level={1} />
          </div>
          {children.length ? (
            <RevealGroup className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {children.map((c) => (
                <RevealItem key={c.path} hover className="card">
                  <Link href={`${c.path}/`} prefetch={false} className="block no-underline">
                    <h2 className="text-[length:var(--step-2)]">{c.nav_label}</h2>
                    <p className="mt-2 text-muted">{c.description}</p>
                  </Link>
                </RevealItem>
              ))}
            </RevealGroup>
          ) : null}
          {page.placeholders.length ? (
            <Reveal className="mt-10 grid gap-4 sm:grid-cols-2">
              {page.placeholders.map((p, i) => (
                <div key={i} role="note" className="placeholder-card">
                  <span className="chip chip-tbc">Placeholder</span>
                  <p className="mt-3 font-medium">{p}</p>
                  <p className="mt-1 text-sm text-muted">To be supplied by {spec.business.name}.</p>
                </div>
              ))}
            </Reveal>
          ) : null}
        </div>
      </section>
      <Sections ctx={ctx} sections={sections} offset={1} />
    </SiteShell>
  );
}
