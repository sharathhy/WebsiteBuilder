import fs from "node:fs";
import path from "node:path";
import { getPreset } from "./presets";
import type { SiteSpec } from "./types";

interface GeneratedFonts {
  faces: string;
  families: { heading?: string; body?: string };
  preload: string[];
}

/** Font faces bundled by scripts/prepare-spec.mjs (self-hosted; nothing fetched remotely). */
export function getFonts(spec: SiteSpec): { css: string; heading: string; body: string; preload: string[] } {
  let gen: GeneratedFonts = { faces: "", families: {}, preload: [] };
  try {
    gen = JSON.parse(fs.readFileSync(path.join(process.cwd(), "src/generated/fonts.json"), "utf8"));
  } catch {
    /* prepare-spec not run: fall back to system stacks */
  }
  const preset = getPreset(spec.template);
  const q = (f?: string) => (f ? `"${f}", ` : "");
  return {
    css: gen.faces,
    heading: `${q(gen.families.heading)}${preset.headingStack}`,
    body: `${q(gen.families.body)}${preset.bodyStack}`,
    preload: gen.preload,
  };
}
