"use client";

import { useEffect } from "react";
import { onIdle } from "@/lib/idle";
import { configureAnalytics, isAnalyticsEnabled, loadAnalyticsScript, track, type AnalyticsConfig } from "@/lib/analytics";

/**
 * Configures analytics and tracks clicks on any element with data-track="event_name"
 * (one delegated listener; no per-link client components). No-op unless enabled.
 */
export function AnalyticsRoot({ config }: { config: AnalyticsConfig }) {
  useEffect(() => {
    configureAnalytics(config);
    if (!isAnalyticsEnabled()) return;
    const cancelIdle = onIdle(() => loadAnalyticsScript(), 4000);
    const onClick = (e: MouseEvent) => {
      const el = (e.target as Element | null)?.closest<HTMLElement>("[data-track]");
      if (el?.dataset.track) track(el.dataset.track, { location: el.dataset.trackLocation ?? "" });
    };
    document.addEventListener("click", onClick, { capture: true });
    return () => {
      document.removeEventListener("click", onClick, { capture: true });
      cancelIdle();
    };
  }, [config]);
  return null;
}
