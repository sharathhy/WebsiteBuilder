// Runs after `next build`: removes the placeholder route a one-page site needs to satisfy
// static export (see src/app/[...slug]/page.tsx).
import fs from "node:fs";
import path from "node:path";

const out = path.resolve(process.cwd(), "out");
for (const name of ["__no-pages", "__no-pages.txt"]) {
  fs.rmSync(path.join(out, name), { recursive: true, force: true });
}
console.log("[postbuild] ok");
