import type { MetadataRoute } from "next";
import { absoluteUrl } from "@/lib/format";
import { getSpec } from "@/lib/spec";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const spec = getSpec();
  const now = new Date();
  return [
    { url: absoluteUrl(spec, "/"), lastModified: now, changeFrequency: "monthly", priority: 1 },
    { url: absoluteUrl(spec, "/privacy/"), lastModified: now, changeFrequency: "yearly", priority: 0.2 },
  ];
}
