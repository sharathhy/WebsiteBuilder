import { ArrowRight, MapPin, Phone } from "lucide-react";
import { luminance } from "@/lib/color";
import { telHref, withBase } from "@/lib/format";
import { effectiveRating } from "@/lib/normalize";
import { Credit, Img, Stars, type SiteCtx } from "../common";
import { Hero3D, type SceneColors } from "./Hero3D";
import { HeroVideo } from "./HeroVideo";

const linkHref = (href: string) => (href.startsWith("/") ? withBase(href) : href);
const trackFor = (href: string) =>
  href.startsWith("tel:") ? "call_click" : href.includes("wa.me") ? "whatsapp_click" : "cta_click";

function Ctas({ ctx, onImage = false }: { ctx: SiteCtx; onImage?: boolean }) {
  const { hero } = ctx.spec;
  const p = hero.cta_primary;
  const s = hero.cta_secondary;
  const ext = (h: string) => /^https?:\/\//.test(h);
  return (
    <div className="mt-8 flex flex-wrap gap-3">
      <a
        href={linkHref(p.href)}
        className="btn btn-primary"
        data-track={trackFor(p.href)}
        data-track-location="hero"
        {...(ext(p.href) ? { target: "_blank", rel: "noopener noreferrer" } : {})}
      >
        {p.href.startsWith("tel:") ? <Phone size={18} aria-hidden="true" /> : null}
        {p.label}
        {!p.href.startsWith("tel:") ? <ArrowRight size={18} aria-hidden="true" /> : null}
      </a>
      {s ? (
        <a
          href={linkHref(s.href)}
          className={`btn ${onImage ? "btn-on-image" : "btn-ghost"}`}
          data-track={trackFor(s.href)}
          data-track-location="hero"
          {...(ext(s.href) ? { target: "_blank", rel: "noopener noreferrer" } : {})}
        >
          {s.label}
        </a>
      ) : null}
    </div>
  );
}

function TrustRow({ ctx, onImage = false }: { ctx: SiteCtx; onImage?: boolean }) {
  const r = effectiveRating(ctx.spec);
  const b = ctx.spec.business;
  const chip = onImage ? "chip !bg-white/12 !text-white backdrop-blur" : "chip";
  return (
    <ul className="mt-8 flex flex-wrap items-center gap-2.5 text-sm" aria-label="Highlights">
      {r.rating != null && r.count != null && r.count > 0 ? (
        <li className={chip}>
          <Stars rating={r.rating} size={14} />
          <span>
            {r.rating.toFixed(1)} · {r.count.toLocaleString(ctx.spec.locale)} {r.source} reviews
          </span>
        </li>
      ) : null}
      <li className={chip}>
        <MapPin size={14} aria-hidden="true" />
        {b.address.city}
      </li>
      {b.phone_e164 && !ctx.spec.hero.cta_primary.href.startsWith("tel:") ? (
        <li>
          <a href={telHref(b.phone_e164)} className={`${chip} min-h-11 no-underline`} data-track="call_click" data-track-location="hero_chip">
            <Phone size={14} aria-hidden="true" />
            {b.phone_display ?? b.phone_e164}
          </a>
        </li>
      ) : null}
    </ul>
  );
}

function Eyebrow({ ctx, onImage = false }: { ctx: SiteCtx; onImage?: boolean }) {
  const b = ctx.spec.business;
  return (
    <p className={`eyebrow ${onImage ? "!text-white/90" : ""}`}>
      {b.category} · {b.address.city}
    </p>
  );
}

/** Image (LCP, server-rendered, eager + fetchpriority=high), optional video, optional 3D layer. */
function Visual({
  ctx,
  className = "",
  imgClass = "",
  sizes,
  canvasClass = "",
  children,
}: {
  ctx: SiteCtx;
  className?: string;
  imgClass?: string;
  sizes: string;
  canvasClass?: string;
  children?: React.ReactNode;
}) {
  const { hero } = ctx.spec;
  const poster = hero.video ? { src: hero.video.poster, alt: hero.fallback_image.alt } : hero.fallback_image;
  return (
    <div className={`hero-visual ${className}`}>
      <Img image={poster} width={1600} height={1067} sizes={sizes} priority className={imgClass} />
      {hero.video ? <HeroVideo video={hero.video} /> : null}
      {children}
      {hero.enable_3d && !hero.video && canvasClass !== "none" ? (
        <Hero3D model={hero.model} colors={sceneColors(ctx)} className={canvasClass} />
      ) : null}
    </div>
  );
}

export function sceneColors(ctx: SiteCtx): SceneColors {
  const t = ctx.tokens;
  return { primary: t.primary, secondary: t.secondary, accent: t.accent, dark: luminance(t.bg) < 0.4 };
}

function HeroCredit({ ctx, className = "" }: { ctx: SiteCtx; className?: string }) {
  const img = ctx.spec.hero.fallback_image;
  if (!img.credit || ctx.spec.hero.video) return null;
  return (
    <p className={`absolute z-[3] ${className}`}>
      <Credit image={img} />
    </p>
  );
}

/* ---------------------------------------------------------------- layouts */

function FullBleed({ ctx }: { ctx: SiteCtx }) {
  const { hero } = ctx.spec;
  const glassPanel = ctx.preset.id === "real-estate";
  return (
    <section aria-labelledby="hero-title" className="hero relative -mt-16 min-h-[100svh] overflow-hidden text-white md:-mt-[72px]">
      <Visual ctx={ctx} className="!absolute inset-0" sizes="100vw" canvasClass="none">
        <div className="absolute inset-0 z-[1] scrim-bottom md:scrim-side" />
      </Visual>
      <div className="relative z-[2] mx-auto grid min-h-[100svh] w-full max-w-[calc(var(--container)+var(--gutter)*2)] grid-rows-[1fr_auto] px-[var(--gutter)] pb-14 pt-28 md:grid-cols-[1.1fr_0.9fr] md:grid-rows-1 md:items-center md:pb-20">
        {hero.enable_3d && !hero.video ? (
          <div className="relative order-1 -mx-[var(--gutter)] min-h-[34svh] md:order-2 md:mx-0 md:h-[70svh]" data-speed="0.25">
            <Hero3D model={hero.model} colors={sceneColors(ctx)} />
          </div>
        ) : (
          <div className="order-1 md:order-2" />
        )}
        <div
          className={`order-2 self-end md:order-1 md:self-center ${
            glassPanel
              ? "rounded-[var(--radius-lg)] border border-white/20 bg-black/35 p-6 backdrop-blur-xl sm:p-10"
              : ""
          }`}
        >
          <Eyebrow ctx={ctx} onImage />
          <h1 id="hero-title" className="h-display mt-4 max-w-[16ch] text-white">
            {hero.headline}
          </h1>
          <p className="mt-5 max-w-[52ch] text-[length:var(--step-1)] leading-relaxed text-white/90">{hero.subheadline}</p>
          <Ctas ctx={ctx} onImage />
          <TrustRow ctx={ctx} onImage />
        </div>
      </div>
      <HeroCredit ctx={ctx} className="right-4 top-20 text-white/80 md:top-24" />
    </section>
  );
}

function Split({ ctx }: { ctx: SiteCtx }) {
  const { hero } = ctx.spec;
  const id = ctx.preset.id;
  return (
    <section aria-labelledby="hero-title" className="hero overflow-hidden">
      {id === "clinic" ? (
        <>
          <div className="glow -left-24 top-10 size-80 bg-primary" data-speed="0.6" aria-hidden="true" />
          <div className="glow right-0 top-1/3 size-96 bg-accent opacity-30" data-speed="0.3" aria-hidden="true" />
        </>
      ) : null}
      {id === "legal-finance" ? <div className="grid-lines absolute inset-0 -z-10 opacity-70" aria-hidden="true" /> : null}
      <div className="container-x grid items-center gap-10 pb-16 pt-10 md:grid-cols-[1.05fr_1fr] md:gap-14 md:pb-24 md:pt-16 lg:min-h-[calc(100svh-72px)]">
        <div>
          <Eyebrow ctx={ctx} />
          <h1 id="hero-title" className="h-display mt-5 max-w-[15ch]">
            {hero.headline}
          </h1>
          <p className="lede mt-6">{hero.subheadline}</p>
          <Ctas ctx={ctx} />
          <TrustRow ctx={ctx} />
        </div>
        <div className="relative">
          {id === "legal-finance" ? (
            <div className="absolute -bottom-4 -right-4 left-6 top-6 rounded-[calc(var(--radius)*0.5)] border border-accent-text/50" aria-hidden="true" />
          ) : null}
          {id === "home-services" ? (
            <div className="absolute -right-3 -top-3 h-2/3 w-2/3 rounded-[var(--radius-lg)] bg-primary" aria-hidden="true" data-speed="0.4" />
          ) : null}
          <Visual
            ctx={ctx}
            className={`aspect-[4/3] shadow-2xl md:aspect-[4/5] ${
              id === "legal-finance" ? "rounded-[calc(var(--radius)*0.5)]" : "rounded-[var(--radius-lg)]"
            }`}
            sizes="(min-width: 768px) 46vw, 100vw"
          >
            <div className="absolute inset-0 z-[1] bg-gradient-to-t from-black/45 via-transparent to-transparent" />
          </Visual>
          <HeroCredit ctx={ctx} className="bottom-3 right-4 text-white/85" />
        </div>
      </div>
    </section>
  );
}

function Arch({ ctx }: { ctx: SiteCtx }) {
  const { hero } = ctx.spec;
  return (
    <section aria-labelledby="hero-title" className="hero overflow-hidden">
      <div className="glow -right-20 top-0 size-96 bg-accent" data-speed="0.5" aria-hidden="true" />
      <div className="container-x grid items-center gap-12 pb-16 pt-10 md:grid-cols-[0.9fr_1.1fr] md:gap-16 md:pb-24 md:pt-14">
        <div className="relative order-2 mx-auto w-full max-w-[460px] md:order-1">
          <Visual ctx={ctx} className="arch aspect-[4/5] shadow-2xl" sizes="(min-width: 768px) 40vw, 90vw" canvasClass="none" />
          {hero.enable_3d && !hero.video ? (
            <div className="absolute -right-10 -top-10 size-56 md:-right-24 md:size-72" data-speed="0.8">
              <Hero3D model={hero.model} colors={sceneColors(ctx)} />
            </div>
          ) : null}
          <div className="absolute -bottom-6 -left-4 hidden rounded-full border border-line bg-bg/80 px-5 py-3 text-sm shadow-lg backdrop-blur md:block">
            <span className="font-heading italic">{ctx.spec.business.tagline}</span>
          </div>
          <HeroCredit ctx={ctx} className="-bottom-12 right-0 text-muted" />
        </div>
        <div className="order-1 text-center md:order-2 md:text-left">
          <Eyebrow ctx={ctx} />
          <h1 id="hero-title" className="h-display mt-5">
            {hero.headline}
          </h1>
          <p className="lede mx-auto mt-6 md:mx-0">{hero.subheadline}</p>
          <div className="flex justify-center md:justify-start">
            <Ctas ctx={ctx} />
          </div>
          <div className="flex justify-center md:justify-start">
            <TrustRow ctx={ctx} />
          </div>
        </div>
      </div>
    </section>
  );
}

function Poster({ ctx }: { ctx: SiteCtx }) {
  const { hero, services } = ctx.spec;
  const ticker = services.map((s) => s.title).slice(0, 8);
  return (
    <section aria-labelledby="hero-title" className="hero overflow-hidden">
      <div className="relative">
        <Visual
          ctx={ctx}
          className="!absolute inset-y-0 right-0 w-full md:w-[58%] md:[clip-path:polygon(18%_0,100%_0,100%_100%,0_100%)]"
          imgClass="opacity-90"
          sizes="(min-width: 768px) 58vw, 100vw"
          canvasClass="none"
        >
          <div className="absolute inset-0 z-[1] bg-gradient-to-t from-bg via-bg/70 to-bg/10 md:bg-gradient-to-r md:from-bg md:via-bg/30 md:to-transparent" />
        </Visual>
        {hero.enable_3d && !hero.video ? (
          <div className="absolute inset-x-0 top-0 z-[2] h-[42%] md:inset-y-0 md:left-auto md:right-0 md:h-full md:w-1/2" data-speed="0.3">
            <Hero3D model={hero.model} colors={sceneColors(ctx)} />
          </div>
        ) : null}
        <div className="container-x relative z-[3] flex min-h-[calc(100svh-64px)] flex-col justify-end pb-14 pt-24 md:min-h-[calc(100svh-72px)] md:justify-center md:pb-24">
          <Eyebrow ctx={ctx} />
          <h1 id="hero-title" className="h-display mt-4 max-w-[12ch]">
            {hero.headline}
          </h1>
          <p className="lede mt-6 !text-fg/85">{hero.subheadline}</p>
          <Ctas ctx={ctx} />
          <TrustRow ctx={ctx} />
        </div>
        <HeroCredit ctx={ctx} className="bottom-3 right-4 text-fg/70" />
      </div>
      {ticker.length ? (
        <div className="overflow-hidden border-y border-line bg-primary py-3 text-on-primary" aria-hidden="true">
          <div className="flex w-max animate-[marquee_28s_linear_infinite] gap-10 whitespace-nowrap font-heading text-xl font-bold uppercase tracking-wide motion-reduce:animate-none">
            {[...ticker, ...ticker, ...ticker, ...ticker].map((t, i) => (
              <span key={i} className="flex items-center gap-10">
                {t} <span className="opacity-60">✦</span>
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function Stage({ ctx }: { ctx: SiteCtx }) {
  const { hero } = ctx.spec;
  return (
    <section aria-labelledby="hero-title" className="hero overflow-hidden">
      <div className="grid-lines absolute inset-0 -z-10" aria-hidden="true" />
      <div className="glow left-[10%] top-10 size-72 bg-primary" data-speed="0.6" aria-hidden="true" />
      <div className="glow right-[8%] top-40 size-80 bg-secondary opacity-40" data-speed="0.35" aria-hidden="true" />
      <div className="container-x relative pt-12 text-center md:pt-20">
        {hero.enable_3d && !hero.video ? (
          <div className="pointer-events-none absolute inset-x-0 -top-4 mx-auto h-[300px] max-w-[520px] opacity-90 md:h-[420px]" data-speed="0.4">
            <Hero3D model={hero.model} colors={sceneColors(ctx)} />
          </div>
        ) : null}
        <div className="relative mx-auto max-w-4xl pt-[180px] md:pt-[250px]">
          <p className="eyebrow justify-center">
            {ctx.spec.business.category} · {ctx.spec.business.address.city}
          </p>
          <h1 id="hero-title" className="h-display grad-text mx-auto mt-5 max-w-[18ch]">
            {hero.headline}
          </h1>
          <p className="lede mx-auto mt-6">{hero.subheadline}</p>
          <div className="flex justify-center">
            <Ctas ctx={ctx} />
          </div>
          <div className="flex justify-center">
            <TrustRow ctx={ctx} />
          </div>
        </div>
      </div>
      <div className="container-x relative mt-14 pb-16 [perspective:1400px] md:mt-20 md:pb-24">
        <div data-tilt className="relative">
          <Visual
            ctx={ctx}
            className="aspect-[16/10] rounded-[var(--radius-lg)] border border-line shadow-2xl md:aspect-[21/9]"
            sizes="(min-width: 1240px) 1200px, 100vw"
            canvasClass="none"
          >
            <div className="absolute inset-0 z-[1] bg-gradient-to-t from-black/30 to-transparent" />
          </Visual>
          <HeroCredit ctx={ctx} className="bottom-3 right-4 text-white/85" />
        </div>
      </div>
    </section>
  );
}

export function Hero({ ctx }: { ctx: SiteCtx }) {
  switch (ctx.preset.heroLayout) {
    case "fullbleed":
      return <FullBleed ctx={ctx} />;
    case "arch":
      return <Arch ctx={ctx} />;
    case "poster":
      return <Poster ctx={ctx} />;
    case "stage":
      return <Stage ctx={ctx} />;
    default:
      return <Split ctx={ctx} />;
  }
}
