// Colour helpers: WCAG contrast and readable foregrounds derived from the spec theme.

export type RGB = [number, number, number];

export function hexToRgb(hex: string): RGB {
  const h = hex.replace("#", "").trim();
  const full = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  if (!/^[0-9a-fA-F]{6}$/.test(full)) throw new Error(`Invalid hex colour: ${hex}`);
  return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16)) as RGB;
}

export function rgbToHex([r, g, b]: RGB): string {
  return (
    "#" +
    [r, g, b]
      .map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0"))
      .join("")
  );
}

function channel(v: number): number {
  const s = v / 255;
  return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
}

/** WCAG 2.x relative luminance */
export function luminance(hex: string): number {
  const [r, g, b] = hexToRgb(hex);
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

/** WCAG 2.x contrast ratio, 1..21 */
export function contrast(a: string, b: string): number {
  const la = luminance(a);
  const lb = luminance(b);
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

/** Linear mix in sRGB; t=0 → a, t=1 → b */
export function mix(a: string, b: string, t: number): string {
  const A = hexToRgb(a);
  const B = hexToRgb(b);
  return rgbToHex([0, 1, 2].map((i) => A[i] + (B[i] - A[i]) * t) as RGB);
}

/** Black or white (slightly softened) — whichever reads better on `bg`. */
export function readableOn(bg: string, light = "#ffffff", dark = "#0b0b0f"): string {
  return contrast(light, bg) >= contrast(dark, bg) ? light : dark;
}

/**
 * Nudge `color` toward black or white until it reaches `ratio` against `bg`.
 * Returns the original colour when it already passes.
 */
export function ensureContrast(color: string, bg: string, ratio = 4.5): string {
  if (contrast(color, bg) >= ratio) return color;
  const target = luminance(bg) > 0.4 ? "#000000" : "#ffffff";
  for (let t = 0.05; t <= 1.0001; t += 0.05) {
    const c = mix(color, target, t);
    if (contrast(c, bg) >= ratio) return c;
  }
  return target;
}

export function withAlpha(hex: string, alpha: number): string {
  const [r, g, b] = hexToRgb(hex);
  return `rgb(${r} ${g} ${b} / ${alpha})`;
}

export interface ThemeTokens {
  bg: string;
  fg: string;
  muted: string;
  surface: string;
  surface2: string;
  border: string;
  primary: string;
  onPrimary: string;
  /** primary adjusted to be readable as text/links on the page background */
  primaryText: string;
  secondary: string;
  onSecondary: string;
  accent: string;
  accentText: string;
  /** dark scrim colour for text placed on photos */
  scrim: string;
}

export function deriveTokens(theme: {
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  foreground: string;
}): ThemeTokens {
  const bg = theme.background;
  const fg = ensureContrast(theme.foreground, bg, 7);
  const isDark = luminance(bg) < 0.4;
  const surface = mix(bg, isDark ? "#ffffff" : fg, isDark ? 0.05 : 0.035);
  const surface2 = mix(bg, isDark ? "#ffffff" : fg, isDark ? 0.09 : 0.07);
  const muted = ensureContrast(mix(fg, bg, 0.32), surface2, 4.6);
  return {
    bg,
    fg,
    muted,
    surface,
    surface2,
    border: mix(bg, fg, isDark ? 0.18 : 0.14),
    primary: theme.primary,
    onPrimary: readableOn(theme.primary),
    primaryText: ensureContrast(theme.primary, surface2, 4.6),
    secondary: theme.secondary,
    onSecondary: readableOn(theme.secondary),
    accent: theme.accent,
    accentText: ensureContrast(theme.accent, surface2, 4.6),
    scrim: isDark ? bg : mix(fg, "#000000", 0.4),
  };
}
