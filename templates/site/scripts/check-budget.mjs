#!/usr/bin/env node
// First-load JS budget for "/": every script referenced by out/index.html (<script src> and
// <link rel="preload|modulepreload" as="script">), gzipped, must total <= BUDGET_KB.
// Also fails if three.js / React Three Fiber code is present in any first-load chunk.
//
// Usage: npm run check:budget [-- --budget 250] [-- --out path/to/out]

import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const arg = (name, dflt) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && args[i + 1] ? args[i + 1] : dflt;
};
const BUDGET_KB = Number(arg("budget", process.env.FIRST_LOAD_BUDGET_KB ?? 250));
const outDir = path.resolve(arg("out", path.join(root, "out")));
const indexPath = path.join(outDir, "index.html");
if (!fs.existsSync(indexPath)) {
  console.error(`[check-budget] ${indexPath} not found — run \`npm run build\` first.`);
  process.exit(1);
}

const html = fs.readFileSync(indexPath, "utf8");
const srcs = new Set();
const nomodule = new Set();
for (const m of html.matchAll(/<script\b[^>]*\bsrc="([^"]+)"[^>]*>/g)) {
  // <script nomodule> (Next's legacy polyfills) is never downloaded by module-capable browsers.
  if (/\bnomodule\b/i.test(m[0])) nomodule.add(m[1]);
  else srcs.add(m[1]);
}
for (const m of html.matchAll(/<link\b[^>]*>/g)) {
  const tag = m[0];
  if (/\brel="(?:preload|modulepreload)"/.test(tag) && (/\bas="script"/.test(tag) || /modulepreload/.test(tag))) {
    const href = tag.match(/\bhref="([^"]+)"/);
    if (href) srcs.add(href[1]);
  }
}

// Strip BASE_PATH / assetPrefix: map "/prefix/_next/..." → out/_next/...
const toFile = (src) => {
  const clean = src.split(/[?#]/)[0];
  const i = clean.indexOf("/_next/");
  return path.join(outDir, i >= 0 ? clean.slice(i + 1) : clean.replace(/^\//, ""));
};

const THREE_MARKERS = [/WebGLRenderer/, /THREE\.WebGLRenderer/, /__THREE__/, /@react-three\/fiber/, /react-three-fiber/];
let total = 0;
let raw = 0;
const rows = [];
const offenders = [];
for (const src of srcs) {
  if (/^https?:\/\//.test(src)) {
    rows.push({ src, gz: 0, note: "external (not counted)" });
    continue;
  }
  const file = toFile(src);
  if (!fs.existsSync(file)) {
    console.error(`[check-budget] referenced script missing: ${src}`);
    process.exit(1);
  }
  const buf = fs.readFileSync(file);
  const gz = zlib.gzipSync(buf, { level: 9 }).length;
  total += gz;
  raw += buf.length;
  const text = buf.toString("utf8");
  if (THREE_MARKERS.some((re) => re.test(text))) offenders.push(src);
  rows.push({ src, gz });
}

rows.sort((a, b) => b.gz - a.gz);
const kb = (n) => (n / 1024).toFixed(1).padStart(7) + " KB";
console.log(`First-load JS for / (${srcs.size} scripts, gzip -9):`);
for (const r of rows) console.log(`  ${kb(r.gz)}  ${r.src}${r.note ? `  (${r.note})` : ""}`);
console.log(`  ${"-".repeat(40)}`);
console.log(`  ${kb(total)}  total gzipped   (${(raw / 1024).toFixed(1)} KB raw)   budget ${BUDGET_KB} KB`);

for (const src of nomodule) {
  const file = toFile(src);
  const gz = fs.existsSync(file) ? zlib.gzipSync(fs.readFileSync(file), { level: 9 }).length : 0;
  console.log(`  (not counted: ${src} is <script nomodule>, legacy-browser polyfills, ${(gz / 1024).toFixed(1)} KB gz)`);
}

let failed = false;
if (offenders.length) {
  console.error(`[check-budget] FAIL: three.js / R3F found in first-load JS: ${offenders.join(", ")}`);
  failed = true;
}
if (total > BUDGET_KB * 1024) {
  console.error(`[check-budget] FAIL: first-load JS ${(total / 1024).toFixed(1)} KB exceeds ${BUDGET_KB} KB`);
  failed = true;
}
if (failed) process.exit(1);
console.log("[check-budget] OK");
