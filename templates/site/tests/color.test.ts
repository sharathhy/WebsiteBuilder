import { describe, expect, it } from "vitest";
import { contrast, deriveTokens, ensureContrast, readableOn } from "@/lib/color";

describe("contrast helpers", () => {
  it("computes WCAG ratios", () => {
    expect(contrast("#000000", "#ffffff")).toBeCloseTo(21, 0);
    expect(contrast("#ffffff", "#ffffff")).toBeCloseTo(1, 5);
  });

  it("picks a readable foreground for primary buttons", () => {
    for (const bg of ["#0f766e", "#d9822b", "#c6f432", "#7c5cff", "#1e3a5f", "#ea580c", "#9d4c5f", "#2f4f4f", "#ffd60a"]) {
      expect(contrast(readableOn(bg), bg)).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("nudges low-contrast colours until they pass", () => {
    const fixed = ensureContrast("#facc15", "#ffffff", 4.5);
    expect(contrast(fixed, "#ffffff")).toBeGreaterThanOrEqual(4.5);
    expect(ensureContrast("#000000", "#ffffff")).toBe("#000000");
  });

  it("derives tokens with AA text contrast for light and dark themes", () => {
    for (const theme of [
      { primary: "#facc15", secondary: "#1d4ed8", accent: "#fde68a", background: "#ffffff", foreground: "#64748b" },
      { primary: "#7c5cff", secondary: "#22d3ee", accent: "#f472b6", background: "#0a0a12", foreground: "#ecebff" },
    ]) {
      const t = deriveTokens(theme);
      expect(contrast(t.fg, t.bg)).toBeGreaterThanOrEqual(7);
      expect(contrast(t.muted, t.bg)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(t.muted, t.surface2)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(t.primaryText, t.bg)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(t.onPrimary, t.primary)).toBeGreaterThanOrEqual(4.5);
    }
  });
});
