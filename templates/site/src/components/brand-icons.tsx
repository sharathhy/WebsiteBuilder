import type { SVGProps } from "react";

// Brand glyphs (lucide no longer ships brand icons). Decorative: always aria-hidden.
type P = SVGProps<SVGSVGElement> & { size?: number };
const base = (size = 20): SVGProps<SVGSVGElement> => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "currentColor",
  "aria-hidden": true,
  focusable: false,
});

export function WhatsAppIcon({ size, ...p }: P) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38a9.9 9.9 0 0 0 4.74 1.21h.01c5.46 0 9.91-4.45 9.91-9.91A9.85 9.85 0 0 0 12.04 2Zm0 18.15h-.01a8.2 8.2 0 0 1-4.19-1.15l-.3-.18-3.12.82.83-3.04-.2-.31a8.2 8.2 0 0 1-1.26-4.38c0-4.54 3.7-8.24 8.25-8.24a8.2 8.2 0 0 1 5.83 2.42 8.18 8.18 0 0 1 2.41 5.83c0 4.54-3.7 8.23-8.24 8.23Zm4.52-6.16c-.25-.12-1.47-.72-1.69-.81-.23-.08-.39-.12-.56.13-.17.24-.64.8-.78.97-.15.16-.29.18-.54.06-.25-.12-1.05-.39-1.99-1.23-.74-.66-1.23-1.47-1.38-1.72-.14-.25-.01-.38.11-.5.11-.11.25-.29.37-.44.13-.14.17-.25.25-.41.08-.17.04-.31-.02-.43-.06-.13-.56-1.34-.76-1.84-.2-.48-.41-.42-.56-.43h-.48a.92.92 0 0 0-.66.31c-.23.25-.87.85-.87 2.07 0 1.22.89 2.4 1.01 2.56.12.17 1.75 2.67 4.23 3.74.59.26 1.05.41 1.41.52.59.19 1.13.16 1.56.1.48-.07 1.47-.6 1.67-1.18.21-.58.21-1.07.15-1.18-.06-.1-.23-.16-.48-.29Z" />
    </svg>
  );
}

function Instagram({ size, ...p }: P) {
  return (
    <svg {...base(size)} fill="none" stroke="currentColor" strokeWidth={2} {...p}>
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}
function Facebook({ size, ...p }: P) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M13.5 21v-7.5h2.5l.4-3h-2.9V8.6c0-.87.25-1.46 1.5-1.46h1.55V4.47A21 21 0 0 0 14.3 4.3c-2.2 0-3.7 1.34-3.7 3.8v2.4H8.1v3h2.5V21h2.9Z" />
    </svg>
  );
}
function LinkedIn({ size, ...p }: P) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M6.94 8.5H3.56V20h3.38V8.5ZM5.25 3A1.97 1.97 0 1 0 5.25 7a1.97 1.97 0 0 0 0-3.94ZM20.44 13.4c0-3.1-1.66-4.54-3.87-4.54a3.34 3.34 0 0 0-3.02 1.66V8.5h-3.38V20h3.38v-5.7c0-1.5.28-2.95 2.14-2.95 1.83 0 1.85 1.72 1.85 3.05V20h3.38l-.48-6.6Z" />
    </svg>
  );
}
function YouTube({ size, ...p }: P) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M21.6 7.2a2.5 2.5 0 0 0-1.77-1.77C18.27 5 12 5 12 5s-6.27 0-7.83.43A2.5 2.5 0 0 0 2.4 7.2 26 26 0 0 0 2 12a26 26 0 0 0 .4 4.8 2.5 2.5 0 0 0 1.77 1.77C5.73 19 12 19 12 19s6.27 0 7.83-.43a2.5 2.5 0 0 0 1.77-1.77A26 26 0 0 0 22 12a26 26 0 0 0-.4-4.8ZM10 15V9l5.2 3L10 15Z" />
    </svg>
  );
}
function XLogo({ size, ...p }: P) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M17.75 3h3.07l-6.7 7.66L22 21h-6.17l-4.83-6.32L5.47 21H2.4l7.17-8.2L2 3h6.33l4.36 5.77L17.75 3Zm-1.08 16.2h1.7L7.4 4.73H5.58L16.67 19.2Z" />
    </svg>
  );
}
function Globe({ size, ...p }: P) {
  return (
    <svg {...base(size)} fill="none" stroke="currentColor" strokeWidth={2} {...p}>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" />
    </svg>
  );
}

export function SocialIcon({ platform, size = 20 }: { platform: string; size?: number }) {
  const p = platform.toLowerCase();
  if (p.includes("insta")) return <Instagram size={size} />;
  if (p.includes("face")) return <Facebook size={size} />;
  if (p.includes("linked")) return <LinkedIn size={size} />;
  if (p.includes("youtu")) return <YouTube size={size} />;
  if (p === "x" || p.includes("twitter")) return <XLogo size={size} />;
  if (p.includes("whatsapp")) return <WhatsAppIcon size={size} />;
  return <Globe size={size} />;
}
