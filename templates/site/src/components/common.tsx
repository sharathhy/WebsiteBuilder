import type { ReactNode } from "react";
import type { ThemeTokens } from "@/lib/color";
import type { TemplatePreset } from "@/lib/presets";
import type { ImageAsset, SiteSpec } from "@/lib/types";
import { withBase } from "@/lib/format";
import { srcSet } from "@/lib/images";
import { Reveal } from "./motion/Reveal";

export interface SiteCtx {
  spec: SiteSpec;
  preset: TemplatePreset;
  tokens: ThemeTokens;
}

export function SectionHeading({
  id,
  eyebrow,
  title,
  lede,
  align = "left",
}: {
  id: string;
  eyebrow?: string;
  title: string;
  lede?: ReactNode;
  align?: "left" | "center";
}) {
  return (
    <Reveal className={align === "center" ? "mx-auto max-w-3xl text-center" : "max-w-3xl"}>
      {eyebrow ? <p className={`eyebrow ${align === "center" ? "justify-center" : ""}`}>{eyebrow}</p> : null}
      <h2 id={id} className="h-section">
        {title}
      </h2>
      {lede ? <div className={`lede mt-4 ${align === "center" ? "mx-auto" : ""}`}>{lede}</div> : null}
    </Reveal>
  );
}

/** "To be confirmed" chip for optional data the business has not published yet. */
export function TbcChip({ children = "To be confirmed" }: { children?: ReactNode }) {
  return <span className="chip chip-tbc">{children}</span>;
}

/** Plain <img> with explicit size (no CLS), lazy by default, srcset for resizable CDNs. */
export function Img({
  image,
  width,
  height,
  className,
  sizes = "100vw",
  priority = false,
}: {
  image: Pick<ImageAsset, "src" | "alt">;
  width: number;
  height: number;
  className?: string;
  sizes?: string;
  priority?: boolean;
}) {
  return (
    <img
      src={withBase(image.src)}
      srcSet={srcSet(image.src)}
      sizes={srcSet(image.src) ? sizes : undefined}
      alt={image.alt}
      width={width}
      height={height}
      className={className}
      loading={priority ? "eager" : "lazy"}
      fetchPriority={priority ? "high" : "auto"}
      decoding={priority ? "sync" : "async"}
    />
  );
}

export function Credit({ image, className = "" }: { image: ImageAsset; className?: string }) {
  if (!image.credit) return null;
  return (
    <span className={`text-xs ${className}`}>
      {image.credit_url ? (
        <a href={image.credit_url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
          {image.credit}
        </a>
      ) : (
        image.credit
      )}
    </span>
  );
}

export function Stars({ rating, size = 18 }: { rating: number; size?: number }) {
  const pct = Math.max(0, Math.min(100, (rating / 5) * 100));
  const row = (
    <span className="flex gap-0.5">
      {[0, 1, 2, 3, 4].map((i) => (
        <svg key={i} width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="currentColor"
            d="M12 2.5l2.94 5.96 6.56.95-4.75 4.63 1.12 6.53L12 17.5l-5.87 3.07 1.12-6.53L2.5 9.41l6.56-.95L12 2.5z"
          />
        </svg>
      ))}
    </span>
  );
  return (
    <span className="relative inline-block leading-none" role="img" aria-label={`Rated ${rating} out of 5`}>
      <span className="opacity-25">{row}</span>
      <span className="absolute inset-0 overflow-hidden text-[#f5b301]" style={{ width: `${pct}%` }}>
        {row}
      </span>
    </span>
  );
}
