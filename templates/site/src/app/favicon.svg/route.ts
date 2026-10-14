import { deriveTokens } from "@/lib/color";
import { initials } from "@/lib/format";
import { getSpec } from "@/lib/spec";

export const dynamic = "force-static";

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

/** Monogram favicon generated from the business initials and theme colours. */
export function GET() {
  const spec = getSpec();
  const t = deriveTokens(spec.theme);
  const r = Math.round(Math.min(spec.theme.radius_px, 24) * 1.4);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="${r}" fill="${t.primary}"/><text x="32" y="33" text-anchor="middle" dominant-baseline="central" font-family="system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif" font-size="28" font-weight="700" fill="${t.onPrimary}">${esc(initials(spec.business.name))}</text></svg>`;
  return new Response(svg, { headers: { "Content-Type": "image/svg+xml" } });
}
