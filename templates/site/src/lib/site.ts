import { deriveTokens } from "./color";
import { getPreset } from "./presets";
import { getSpec } from "./spec";
import type { SiteCtx } from "@/components/common";

export function getSiteCtx(): SiteCtx {
  const spec = getSpec();
  return { spec, preset: getPreset(spec.template), tokens: deriveTokens(spec.theme) };
}
