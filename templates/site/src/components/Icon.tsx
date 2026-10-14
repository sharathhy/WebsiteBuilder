// Server-only: renders a lucide icon by its kebab-case name from the spec (e.g. "stethoscope").
// Only import this from server components so the full icon map never reaches the client bundle.
import { createElement } from "react";
import { icons, Sparkles, type LucideIcon } from "lucide-react";

const pascal = (name: string) =>
  name
    .trim()
    .replace(/Icon$/, "")
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join("");

export function resolveIcon(name: string): LucideIcon {
  const map = icons as Record<string, LucideIcon>;
  return map[pascal(name)] ?? map[name] ?? Sparkles;
}

export function Icon({ name, size = 22, className }: { name: string; size?: number; className?: string }) {
  return createElement(resolveIcon(name), { size, strokeWidth: 1.75, "aria-hidden": true, focusable: false, className });
}
