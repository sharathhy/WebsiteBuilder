// Tiny analytics hook. track() is a no-op unless spec.analytics.enabled.

export interface AnalyticsConfig {
  enabled: boolean;
  provider: "plausible" | "ga4" | null;
  id: string | null;
}

type Props = Record<string, string | number | boolean>;

declare global {
  interface Window {
    plausible?: ((event: string, opts?: { props?: Props }) => void) & { q?: unknown[] };
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

let config: AnalyticsConfig = { enabled: false, provider: null, id: null };

export function configureAnalytics(next: AnalyticsConfig): void {
  config = next;
}

export function isAnalyticsEnabled(): boolean {
  return config.enabled && !!config.provider && !!config.id;
}

export function track(event: string, props: Props = {}): void {
  if (!isAnalyticsEnabled() || typeof window === "undefined") return;
  try {
    if (config.provider === "plausible") {
      window.plausible?.(event, { props });
    } else if (config.provider === "ga4") {
      window.gtag?.("event", event, props);
    }
  } catch {
    /* analytics must never break the page */
  }
}

/** Inject the provider script after the page is idle (never render-blocking). */
export function loadAnalyticsScript(): void {
  if (!isAnalyticsEnabled() || typeof document === "undefined") return;
  const s = document.createElement("script");
  s.defer = true;
  if (config.provider === "plausible") {
    window.plausible =
      window.plausible ||
      Object.assign(
        (...args: unknown[]) => {
          (window.plausible!.q = window.plausible!.q || []).push(args);
        },
        { q: [] as unknown[] },
      );
    s.src = "https://plausible.io/js/script.js";
    s.setAttribute("data-domain", config.id!);
  } else {
    window.dataLayer = window.dataLayer || [];
    window.gtag = function gtag() {
      // gtag.js requires the real `arguments` object, not an array.
      // eslint-disable-next-line prefer-rest-params
      window.dataLayer!.push(arguments);
    };
    window.gtag("js", new Date());
    window.gtag("config", config.id);
    s.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(config.id!)}`;
    s.async = true;
  }
  document.head.appendChild(s);
}
