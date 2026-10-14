import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const CATEGORY_LABELS: Record<string, string> = {
  performance: "Performance",
  seo: "SEO",
  mobile: "Mobile",
  design: "Visual design",
  accessibility: "Accessibility",
  trust: "Trust & credibility",
  conversion: "Conversion",
  tech: "Tech",
};
