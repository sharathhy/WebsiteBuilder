import type { Address, Day, HoursRow, SiteSpec } from "./types";
import { DAYS } from "./types";

const CURRENCY_SYMBOL: Record<SiteSpec["currency"], string> = { INR: "₹", USD: "$" };

export function currencySymbol(currency: SiteSpec["currency"]): string {
  return CURRENCY_SYMBOL[currency];
}

/**
 * Prices are free text in the spec ("1500", "₹1,500", "From 2500", "On request").
 * Bare numbers are formatted as currency for the locale (en-IN groups lakhs: ₹1,50,000);
 * anything else is shown exactly as written, with a bare leading number localised.
 */
export function formatPrice(price: string, locale: SiteSpec["locale"], currency: SiteSpec["currency"]): string {
  const p = price.trim();
  const fmt = (n: number) =>
    new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
      maximumFractionDigits: Number.isInteger(n) ? 0 : 2,
      minimumFractionDigits: 0,
    }).format(n);
  if (/^\d+(\.\d+)?$/.test(p.replace(/,/g, ""))) return fmt(Number(p.replace(/,/g, "")));
  // "From 1500" / "1500/month" / "1500 per session" → localise the number, keep the words.
  if (!/[₹$€£]/.test(p) && !/\b(rs\.?|inr|usd)\b/i.test(p)) {
    return p.replace(/(\d[\d,]*(?:\.\d+)?)/, (m) => fmt(Number(m.replace(/,/g, ""))));
  }
  return p;
}

export function formatTime(hhmm: string, locale: SiteSpec["locale"]): string {
  const [h, m] = hhmm.split(":").map(Number);
  if (h === 24 && m === 0) return locale === "en-US" ? "Midnight" : "midnight";
  const d = new Date(Date.UTC(2020, 0, 1, h % 24, m));
  return new Intl.DateTimeFormat(locale, { hour: "numeric", minute: "2-digit", timeZone: "UTC" }).format(d);
}

export function telHref(e164: string): string {
  return `tel:${e164.replace(/[^\d+]/g, "")}`;
}

export function whatsappHref(e164: string, text?: string): string {
  const digits = e164.replace(/\D/g, "");
  return `https://wa.me/${digits}${text ? `?text=${encodeURIComponent(text)}` : ""}`;
}

export function displayPhone(spec: SiteSpec): string | null {
  return spec.business.phone_display ?? spec.business.phone_e164;
}

export function addressLines(a: Address): string[] {
  const line2 = [a.city, [a.state, a.postal_code].filter(Boolean).join(" ")].filter(Boolean).join(", ");
  return [a.street, line2, a.country === "IN" ? "India" : "United States"].filter(Boolean);
}

export function initials(name: string): string {
  const words = name
    .replace(/[^\p{L}\p{N}\s&]/gu, " ")
    .split(/\s+/)
    .filter((w) => w && !/^(the|and|&|of)$/i.test(w));
  return (words.length >= 2 ? words[0][0] + words[1][0] : (words[0] ?? "L").slice(0, 2)).toUpperCase();
}

/** Group hours by day in Monday..Sunday order (multiple rows per day = split shifts). */
export function hoursByDay(rows: HoursRow[]): { day: Day; slots: { opens: string; closes: string }[] }[] {
  return DAYS.map((day) => ({
    day,
    slots: rows
      .filter((r) => r.day === day)
      .map((r) => ({ opens: r.opens, closes: r.closes }))
      .sort((a, b) => a.opens.localeCompare(b.opens)),
  }));
}

const toMin = (hhmm: string) => {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
};

/**
 * Is the business open at `day` + `minutes` (local business time)? Handles overnight slots
 * (closes <= opens, e.g. 18:00–02:00) by checking the previous day's spill-over.
 */
export function isOpenAt(rows: HoursRow[], day: Day, minutes: number): boolean {
  const idx = DAYS.indexOf(day);
  const prev = DAYS[(idx + 6) % 7];
  for (const r of rows) {
    const o = toMin(r.opens);
    let c = toMin(r.closes);
    const overnight = c <= o;
    if (overnight) c += 24 * 60;
    if (r.day === day && minutes >= o && minutes < c) return true;
    if (overnight && r.day === prev && minutes + 24 * 60 < c) return true;
  }
  return false;
}

const US_STATE_TZ: Record<string, string> = {
  CA: "America/Los_Angeles", WA: "America/Los_Angeles", OR: "America/Los_Angeles", NV: "America/Los_Angeles",
  AZ: "America/Phoenix", CO: "America/Denver", UT: "America/Denver", NM: "America/Denver", MT: "America/Denver",
  ID: "America/Boise", WY: "America/Denver", TX: "America/Chicago", IL: "America/Chicago", MN: "America/Chicago",
  WI: "America/Chicago", MO: "America/Chicago", LA: "America/Chicago", OK: "America/Chicago", KS: "America/Chicago",
  NE: "America/Chicago", IA: "America/Chicago", AR: "America/Chicago", MS: "America/Chicago", AL: "America/Chicago",
  TN: "America/Chicago", HI: "Pacific/Honolulu", AK: "America/Anchorage",
};

/** Best-effort IANA timezone for the business (defaults: India → Kolkata, US → New York). */
export function businessTimeZone(a: Address): string {
  if (a.country === "IN") return "Asia/Kolkata";
  const st = (a.state ?? "").trim().toUpperCase();
  return US_STATE_TZ[st] ?? "America/New_York";
}

export function safeUrl(base: string): URL {
  try {
    return new URL(base);
  } catch {
    return new URL("https://example.com");
  }
}

/**
 * Absolute URL under spec.site_url. site_url already includes any BASE_PATH sub-path
 * (e.g. https://host/previews/x), so paths are appended, never resolved against the origin.
 */
export function absoluteUrl(spec: SiteSpec, p = "/"): string {
  const base = safeUrl(spec.site_url).toString().replace(/\/+$/, "");
  const rel = p.replace(/^\/+/, "");
  return rel ? `${base}/${rel}` : `${base}/`;
}

/** Build-time sub-path (env BASE_PATH, e.g. "/previews/abc"); "" when served from "/". */
export function basePath(): string {
  const raw = (typeof process !== "undefined" && process.env.BASE_PATH) || "";
  const trimmed = raw.trim().replace(/\/+$/, "");
  if (!trimmed) return "";
  return trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
}

/** Prefix root-relative local asset paths ("/samples/x.svg") with BASE_PATH; leave URLs alone. */
export function withBase(src: string): string {
  if (!src.startsWith("/") || src.startsWith("//")) return src;
  const bp = basePath();
  return bp && !src.startsWith(bp + "/") ? bp + src : src;
}

export function paragraphs(text: string): string[] {
  return text
    .split(/\n\s*\n/)
    .map((s) => s.trim())
    .filter(Boolean);
}
