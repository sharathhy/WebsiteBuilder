#!/usr/bin/env node
// Runs before `next build`:
//  1. resolves the spec (env SITE_SPEC, absolute path; default ./site.json)
//  2. validates it against ../site-spec.schema.json (the Pydantic-generated contract)
//  3. bundles the spec's fonts (latin + latin-ext subsets) into public/fonts
//  4. copies local sample art referenced by the spec (/samples/...) and SITE_ASSETS_DIR
// Everything it writes is gitignored and rewritten on every build.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const log = (...a) => console.log("[prepare-spec]", ...a);
const fail = (msg) => {
  console.error(`[prepare-spec] ERROR: ${msg}`);
  process.exit(1);
};

// 1. spec ------------------------------------------------------------------------------
const specPath = process.env.SITE_SPEC?.trim() ? path.resolve(process.env.SITE_SPEC) : path.join(root, "site.json");
if (!fs.existsSync(specPath)) fail(`spec not found: ${specPath} (set SITE_SPEC to an absolute path)`);
let spec;
try {
  spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
} catch (e) {
  fail(`spec is not valid JSON (${specPath}): ${e.message}`);
}
log(`spec: ${specPath} (template=${spec.template}, business=${JSON.stringify(spec.business?.name)})`);

// 2. schema validation -----------------------------------------------------------------
const schemaPath = process.env.SITE_SPEC_SCHEMA?.trim()
  ? path.resolve(process.env.SITE_SPEC_SCHEMA)
  : path.join(root, "..", "site-spec.schema.json");
if (fs.existsSync(schemaPath)) {
  const ajv = new Ajv2020({ allErrors: true, strict: false });
  addFormats(ajv);
  const validate = ajv.compile(JSON.parse(fs.readFileSync(schemaPath, "utf8")));
  if (!validate(spec)) {
    const errs = validate.errors.map((e) => `  ${e.instancePath || "/"} ${e.message}`).join("\n");
    fail(`spec does not match ${path.relative(process.cwd(), schemaPath)}:\n${errs}`);
  }
  log("schema: valid");
} else {
  log(`WARNING: schema not found at ${schemaPath}; skipping validation`);
}

// Soft content checks: warn, never invent.
for (const s of spec.sections ?? []) {
  const empty =
    (s === "services" && !spec.services?.length) ||
    (s === "gallery" && !spec.gallery?.length) ||
    (s === "faq" && !spec.faq?.length) ||
    (s === "pricing" && !spec.pricing?.length) ||
    (s === "about" && !spec.about) ||
    (s === "hours" && !spec.business?.hours?.length);
  if (empty) log(`note: section "${s}" has no content in the spec and will be omitted`);
}

// 3. fonts -----------------------------------------------------------------------------
const FONT_MAP = JSON.parse(fs.readFileSync(path.join(root, "src/lib/fonts.json"), "utf8"));
const fontKey = (name) => String(name ?? "").toLowerCase().replace(/variable/g, "").replace(/[^a-z0-9]/g, "");
const fontsDir = path.join(root, "public/fonts");
fs.rmSync(fontsDir, { recursive: true, force: true });
fs.mkdirSync(fontsDir, { recursive: true });

const fontOut = { faces: "", families: {}, preload: [] };
const wanted = { heading: spec.theme?.font_heading ?? "Inter", body: spec.theme?.font_body ?? "Inter" };
const done = new Set();
for (const [role, name] of Object.entries(wanted)) {
  const entry = FONT_MAP[fontKey(name)];
  if (!entry) {
    log(`font "${name}" (${role}) is not bundled; using the template's system font stack`);
    continue;
  }
  fontOut.families[role] = entry.family;
  if (done.has(entry.pkg)) continue;
  done.add(entry.pkg);
  const pkgDir = path.join(root, "node_modules/@fontsource-variable", entry.pkg);
  const css = fs.readFileSync(path.join(pkgDir, "wght.css"), "utf8");
  const blocks = css.split(/(?=\/\*)/).filter((b) => /-latin(-ext)?-wght-normal \*\//.test(b));
  for (const block of blocks) {
    const m = block.match(/url\(\.\/files\/([^)]+\.woff2)\)/);
    if (!m) continue;
    fs.copyFileSync(path.join(pkgDir, "files", m[1]), path.join(fontsDir, m[1]));
    fontOut.faces += block.replace(/url\(\.\/files\//g, "url(/fonts/").trim() + "\n";
    if (/-latin-wght-normal/.test(m[1])) fontOut.preload.push(`/fonts/${m[1]}`);
  }
}
const genDir = path.join(root, "src/generated");
fs.mkdirSync(genDir, { recursive: true });
fs.writeFileSync(path.join(genDir, "fonts.json"), JSON.stringify(fontOut, null, 2));
log(`fonts: ${Object.values(fontOut.families).join(", ") || "system stacks"}`);

// 4. local assets ----------------------------------------------------------------------
const samplesOut = path.join(root, "public/samples");
fs.rmSync(samplesOut, { recursive: true, force: true });
const srcs = new Set();
const collect = (v) => {
  if (Array.isArray(v)) v.forEach(collect);
  else if (v && typeof v === "object") Object.values(v).forEach(collect);
  else if (typeof v === "string" && v.startsWith("/samples/")) srcs.add(v.split(/[?#]/)[0]);
};
collect(spec);
for (const s of srcs) {
  const from = path.join(root, "sample-assets", s.slice("/samples/".length));
  if (!fs.existsSync(from)) {
    log(`WARNING: sample asset missing: ${s}`);
    continue;
  }
  const to = path.join(samplesOut, s.slice("/samples/".length));
  fs.mkdirSync(path.dirname(to), { recursive: true });
  fs.copyFileSync(from, to);
}
if (srcs.size) log(`samples: copied ${srcs.size} file(s)`);

const assetsOut = path.join(root, "public/assets");
fs.rmSync(assetsOut, { recursive: true, force: true });
if (process.env.SITE_ASSETS_DIR?.trim()) {
  const from = path.resolve(process.env.SITE_ASSETS_DIR);
  if (!fs.existsSync(from)) fail(`SITE_ASSETS_DIR not found: ${from}`);
  fs.cpSync(from, assetsOut, { recursive: true });
  log(`assets: copied ${from} -> public/assets`);
}
