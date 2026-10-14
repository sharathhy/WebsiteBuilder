/**
 * Responsive srcset for image CDNs that resize via query params (Unsplash/imgix).
 * Other URLs are used as-is (no srcset) — width/height attributes still prevent layout shift.
 */
const RESIZABLE = /^https:\/\/(images\.unsplash\.com|[a-z0-9-]+\.imgix\.net)\//i;

export function srcSet(src: string, widths: number[] = [480, 768, 1080, 1440, 1920]): string | undefined {
  if (!RESIZABLE.test(src)) return undefined;
  try {
    return widths
      .map((w) => {
        const u = new URL(src);
        u.searchParams.set("w", String(w));
        if (!u.searchParams.has("auto")) u.searchParams.set("auto", "format");
        if (!u.searchParams.has("fit")) u.searchParams.set("fit", "crop");
        if (!u.searchParams.has("q")) u.searchParams.set("q", "70");
        return `${u.toString()} ${w}w`;
      })
      .join(", ");
  } catch {
    return undefined;
  }
}

export function imageOrigin(src: string): string | null {
  try {
    const u = new URL(src);
    return u.protocol === "https:" ? u.origin : null;
  } catch {
    return null;
  }
}
