import fs from "node:fs";
import path from "node:path";
import { normalizeSpec } from "./normalize";
import type { SiteSpec } from "./types";

let cached: { path: string; spec: SiteSpec } | null = null;

export function specPath(): string {
  const fromEnv = process.env.SITE_SPEC;
  return fromEnv && fromEnv.trim() !== "" ? path.resolve(fromEnv) : path.join(process.cwd(), "site.json");
}

/** Read the site spec at build time. The spec file is the only input to the site. */
export function getSpec(): SiteSpec {
  const p = specPath();
  if (cached && cached.path === p) return cached.spec;
  const raw = JSON.parse(fs.readFileSync(p, "utf8"));
  const spec = normalizeSpec(raw);
  cached = { path: p, spec };
  return spec;
}
