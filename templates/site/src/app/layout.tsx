import type { Metadata, Viewport } from "next";
import type { CSSProperties, ReactNode } from "react";
import { preload } from "react-dom";
import "./globals.css";
import { AnalyticsRoot } from "@/components/AnalyticsRoot";
import { MotionProvider } from "@/components/motion/MotionProvider";
import { ScrollFX } from "@/components/motion/ScrollFX";
import { absoluteUrl, withBase } from "@/lib/format";
import { getFonts } from "@/lib/fonts";
import { imageOrigin } from "@/lib/images";
import { buildFaqJsonLd, buildLocalBusinessJsonLd, jsonLdString } from "@/lib/jsonld";
import { getSiteCtx } from "@/lib/site";

export function generateMetadata(): Metadata {
  const { spec } = getSiteCtx();
  const url = absoluteUrl(spec, "/");
  const ogImage = absoluteUrl(spec, "/og.png");
  return {
    metadataBase: new URL(url),
    title: spec.seo.title,
    description: spec.seo.description,
    keywords: [spec.seo.primary_keyword, ...spec.seo.keywords].filter(Boolean),
    applicationName: spec.business.name,
    alternates: { canonical: url },
    openGraph: {
      type: "website",
      url,
      siteName: spec.business.name,
      title: spec.seo.title,
      description: spec.seo.description,
      locale: spec.locale.replace("-", "_"),
      images: [{ url: ogImage, width: 1200, height: 630, alt: spec.business.name }],
    },
    twitter: { card: "summary_large_image", title: spec.seo.title, description: spec.seo.description, images: [ogImage] },
    icons: {
      icon: [{ url: withBase("/favicon.svg"), type: "image/svg+xml" }],
      apple: [{ url: withBase("/icon-512.png"), sizes: "512x512", type: "image/png" }],
    },
    manifest: withBase("/manifest.webmanifest"),
    formatDetection: { telephone: false },
  };
}

export function generateViewport(): Viewport {
  const { tokens, spec } = getSiteCtx();
  return {
    width: "device-width",
    initialScale: 1,
    themeColor: tokens.bg,
    colorScheme: spec.theme.mode === "dark" ? "dark" : "light",
  };
}

export default function RootLayout({ children }: { children: ReactNode }) {
  const ctx = getSiteCtx();
  const { spec, preset, tokens } = ctx;
  const fonts = getFonts(spec);
  for (const href of fonts.preload) preload(withBase(href), { as: "font", type: "font/woff2", crossOrigin: "anonymous" });
  const heroOrigin = imageOrigin(spec.hero.video?.poster ?? spec.hero.fallback_image.src);

  const style = {
    "--c-bg": tokens.bg,
    "--c-fg": tokens.fg,
    "--c-muted": tokens.muted,
    "--c-surface": tokens.surface,
    "--c-surface-2": tokens.surface2,
    "--c-border": tokens.border,
    "--c-primary": tokens.primary,
    "--c-on-primary": tokens.onPrimary,
    "--c-primary-text": tokens.primaryText,
    "--c-secondary": tokens.secondary,
    "--c-on-secondary": tokens.onSecondary,
    "--c-accent": tokens.accent,
    "--c-accent-text": tokens.accentText,
    "--c-scrim": tokens.scrim,
    "--f-heading": fonts.heading,
    "--f-body": fonts.body,
    "--radius": `${spec.theme.radius_px}px`,
  } as CSSProperties;

  const faq = buildFaqJsonLd(spec);
  const fontCss = fonts.css.replace(/url\(\/fonts\//g, `url(${withBase("/fonts/")}`);

  return (
    <html
      lang={spec.locale}
      dir="ltr"
      data-template={spec.template}
      data-card={preset.cardStyle}
      data-mode={spec.theme.mode}
      style={style}
      suppressHydrationWarning
    >
      <head>
        {spec.noindex ? <meta name="robots" content="noindex,nofollow" /> : null}
        {heroOrigin ? <link rel="preconnect" href={heroOrigin} crossOrigin="" /> : null}
        {fontCss ? <style dangerouslySetInnerHTML={{ __html: fontCss }} /> : null}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: jsonLdString(buildLocalBusinessJsonLd(spec)) }}
        />
        {faq ? <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLdString(faq) }} /> : null}
        <noscript>
          {/* Without JS, entrance animations never run: show everything. */}
          <style>{`[style*="opacity:0"],[style*="opacity: 0"]{opacity:1!important;transform:none!important}.hero-canvas{display:none}`}</style>
        </noscript>
      </head>
      <body>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <MotionProvider motion={preset.motion}>{children}</MotionProvider>
        <ScrollFX parallax={preset.motion.parallax} />
        <AnalyticsRoot config={spec.analytics} />
      </body>
    </html>
  );
}
