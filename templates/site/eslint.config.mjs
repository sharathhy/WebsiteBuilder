import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const config = [
  ...nextVitals,
  ...nextTs,
  {
    ignores: [".next/**", "out/**", "node_modules/**", "next-env.d.ts", "public/**"],
  },
  {
    rules: {
      // Spec images are arbitrary remote URLs rendered with explicit width/height; next/image
      // optimisation is unavailable in a static export.
      "@next/next/no-img-element": "off",
    },
  },
];

export default config;
