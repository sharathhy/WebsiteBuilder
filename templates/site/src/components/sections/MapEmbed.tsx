"use client";

import { MapPin } from "lucide-react";
import { useEffect, useRef, useState } from "react";

/**
 * Google Maps embed, loaded only after the user asks for it or it scrolls near the viewport.
 * Until then (and without JS) a link to google_maps_url is the fallback.
 */
export function MapEmbed({ lat, lng, title, mapsUrl }: { lat: number; lng: number; title: string; mapsUrl: string | null }) {
  const ref = useRef<HTMLDivElement>(null);
  const [load, setLoad] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || load || !("IntersectionObserver" in window)) return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setLoad(true);
          io.disconnect();
        }
      },
      { rootMargin: "200px 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [load]);

  const src = `https://www.google.com/maps?q=${lat},${lng}&output=embed`;
  return (
    <div ref={ref} className="relative aspect-[4/3] w-full overflow-hidden rounded-[var(--radius)] border border-line bg-surface-2 md:aspect-[16/11]">
      {load ? (
        <iframe
          src={src}
          title={title}
          className="absolute inset-0 h-full w-full border-0"
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
          allowFullScreen
        />
      ) : (
        <div className="grid-lines absolute inset-0 grid place-items-center p-6 text-center">
          <div className="grid justify-items-center gap-3">
            <span className="icon-chip" aria-hidden="true">
              <MapPin size={22} />
            </span>
            <button type="button" className="btn btn-primary" onClick={() => setLoad(true)} data-track="map_open">
              Show map
            </button>
            {mapsUrl ? (
              <a href={mapsUrl} className="underline underline-offset-4" target="_blank" rel="noopener noreferrer">
                Open in Google Maps
              </a>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
