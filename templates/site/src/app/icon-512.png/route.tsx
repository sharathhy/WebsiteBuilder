import { ImageResponse } from "next/og";
import { deriveTokens } from "@/lib/color";
import { initials } from "@/lib/format";
import { getSpec } from "@/lib/spec";

export const dynamic = "force-static";

export function GET() {
  const spec = getSpec();
  const t = deriveTokens(spec.theme);
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: t.primary,
          color: t.onPrimary,
          fontSize: 220,
          fontWeight: 700,
        }}
      >
        {initials(spec.business.name)}
      </div>
    ),
    { width: 512, height: 512 },
  );
}
