// Client-safe BASE_PATH prefixing (NEXT_PUBLIC_BASE_PATH is inlined by next.config.ts).
export function withBasePublic(src: string): string {
  if (!src.startsWith("/") || src.startsWith("//")) return src;
  const bp = process.env.NEXT_PUBLIC_BASE_PATH || "";
  return bp && !src.startsWith(bp + "/") ? bp + src : src;
}
