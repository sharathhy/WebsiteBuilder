"use client";

import { useIsClient, useMediaQuery } from "@/lib/use-media";
import type { VideoAsset } from "@/lib/types";
import { withBasePublic } from "@/lib/client-base";

/**
 * Muted looping hero video. The poster is rendered server-side as an <img> (the LCP element);
 * the <video> is mounted after hydration and never for prefers-reduced-motion (poster only).
 */
export function HeroVideo({ video }: { video: VideoAsset }) {
  const client = useIsClient();
  const reduce = useMediaQuery("(prefers-reduced-motion: reduce)");
  const saveData =
    client && !!(navigator as Navigator & { connection?: { saveData?: boolean } }).connection?.saveData;
  if (!client || reduce || saveData) return null;
  return (
    <video
      className="absolute inset-0 h-full w-full object-cover"
      autoPlay
      muted
      loop
      playsInline
      preload="metadata"
      poster={withBasePublic(video.poster)}
      aria-hidden="true"
      tabIndex={-1}
    >
      <source src={withBasePublic(video.webm)} type="video/webm" />
      <source src={withBasePublic(video.mp4)} type="video/mp4" />
    </video>
  );
}
