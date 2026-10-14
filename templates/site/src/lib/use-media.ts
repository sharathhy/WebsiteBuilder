"use client";

import { useSyncExternalStore } from "react";

/** Subscribe to a media query; always false during SSR/hydration (motion-off default). */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (cb) => {
      const mq = window.matchMedia(query);
      mq.addEventListener?.("change", cb);
      return () => mq.removeEventListener?.("change", cb);
    },
    () => window.matchMedia(query).matches,
    () => false,
  );
}

/** True only on the client once hydrated (false on the server snapshot). */
export function useIsClient(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
}
