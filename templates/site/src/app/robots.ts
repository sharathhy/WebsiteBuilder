import type { MetadataRoute } from "next";
import { absoluteUrl } from "@/lib/format";
import { getSpec } from "@/lib/spec";

export const dynamic = "force-static";

export default function robots(): MetadataRoute.Robots {
  const spec = getSpec();
  if (spec.noindex) return { rules: { userAgent: "*", disallow: "/" } };
  return { rules: { userAgent: "*", allow: "/" }, sitemap: absoluteUrl(spec, "/sitemap.xml") };
}
