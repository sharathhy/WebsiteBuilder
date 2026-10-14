import type { MetadataRoute } from "next";
import { absoluteUrl } from "@/lib/format";
import { getSpec } from "@/lib/spec";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const spec = getSpec();
  const now = new Date();
  return [
    { url: absoluteUrl(spec, "/"), lastModified: now, changeFrequency: "monthly", priority: 1 },
    ...spec.pages.map((p) => ({
      url: absoluteUrl(spec, `${p.path}/`),
      lastModified: now,
      changeFrequency: "monthly" as const,
      priority: p.parent ? 0.6 : 0.8,
    })),
    { url: absoluteUrl(spec, "/privacy/"), lastModified: now, changeFrequency: "yearly", priority: 0.2 },
  ];
}
