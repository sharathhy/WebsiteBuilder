import type { NextConfig } from "next";

// Optional sub-path deployment, e.g. BASE_PATH=/previews/sample-dental-1a2b
const rawBase = (process.env.BASE_PATH ?? "").trim().replace(/\/+$/, "");
const basePath = rawBase ? (rawBase.startsWith("/") ? rawBase : `/${rawBase}`) : "";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  reactStrictMode: true,
  poweredByHeader: false,
  images: { unoptimized: true },
  productionBrowserSourceMaps: false,
  ...(basePath ? { basePath, assetPrefix: basePath } : {}),
  env: {
    // exposed to client code that needs to build local URLs (e.g. preview assets)
    NEXT_PUBLIC_BASE_PATH: basePath,
  },
};

export default nextConfig;
