import type { MetadataRoute } from "next";
import { deriveTokens } from "@/lib/color";
import { withBase } from "@/lib/format";
import { getSpec } from "@/lib/spec";

export const dynamic = "force-static";

export default function manifest(): MetadataRoute.Manifest {
  const spec = getSpec();
  const t = deriveTokens(spec.theme);
  return {
    name: spec.business.name,
    short_name: spec.business.name.length > 12 ? spec.business.name.split(/\s+/)[0] : spec.business.name,
    description: spec.seo.description,
    start_url: withBase("/"),
    scope: withBase("/"),
    display: "standalone",
    background_color: t.bg,
    theme_color: t.primary,
    lang: spec.locale,
    icons: [
      { src: withBase("/favicon.svg"), sizes: "any", type: "image/svg+xml" },
      { src: withBase("/icon-512.png"), sizes: "512x512", type: "image/png", purpose: "any" },
    ],
  };
}
