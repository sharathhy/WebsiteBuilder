import { ImageResponse } from "next/og";
import { deriveTokens, mix } from "@/lib/color";
import { initials } from "@/lib/format";
import { getSpec } from "@/lib/spec";

export const dynamic = "force-static";

/** 1200×630 Open Graph card rendered at build time (no remote fonts or images). */
export function GET() {
  const spec = getSpec();
  const t = deriveTokens(spec.theme);
  const b = spec.business;
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 72,
          background: `linear-gradient(135deg, ${t.bg} 0%, ${mix(t.bg, t.primary, 0.22)} 100%)`,
          color: t.fg,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <div
            style={{
              width: 96,
              height: 96,
              borderRadius: 24,
              background: t.primary,
              color: t.onPrimary,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 44,
              fontWeight: 700,
            }}
          >
            {initials(b.name)}
          </div>
          <div style={{ display: "flex", fontSize: 30, color: t.muted }}>
            {b.category} · {b.address.city}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ display: "flex", fontSize: 76, fontWeight: 700, lineHeight: 1.05, letterSpacing: -2 }}>{b.name}</div>
          <div style={{ display: "flex", fontSize: 34, color: t.muted, maxWidth: 980 }}>{b.tagline}</div>
        </div>
        <div style={{ display: "flex", height: 10, width: 220, borderRadius: 10, background: t.primary }} />
      </div>
    ),
    { width: 1200, height: 630 },
  );
}
