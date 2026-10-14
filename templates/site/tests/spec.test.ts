import fs from "node:fs";
import path from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { describe, expect, it } from "vitest";
import { buildFaqJsonLd, buildLocalBusinessJsonLd, jsonLdString, schemaType } from "@/lib/jsonld";
import { absoluteUrl, formatPrice, formatTime, isOpenAt } from "@/lib/format";
import { normalizeSpec } from "@/lib/normalize";

const examplesDir = path.resolve(__dirname, "../../examples");
const schema = JSON.parse(fs.readFileSync(path.resolve(__dirname, "../../site-spec.schema.json"), "utf8"));
const examples = fs.readdirSync(examplesDir).filter((f) => f.endsWith(".json"));
const load = (f: string) => JSON.parse(fs.readFileSync(path.join(examplesDir, f), "utf8"));

describe("example specs", () => {
  const ajv = new Ajv2020({ allErrors: true, strict: false });
  addFormats(ajv);
  const validate = ajv.compile(schema);

  it("has one example per template", () => {
    expect(examples.sort()).toEqual(
      ["clinic", "fitness", "generic-premium", "home-services", "legal-finance", "real-estate", "restaurant", "salon"].map((t) => `${t}.json`),
    );
  });

  it.each(examples)("%s validates against site-spec.schema.json", (f) => {
    const ok = validate(load(f));
    expect(validate.errors ?? []).toEqual([]);
    expect(ok).toBe(true);
  });

  it.each(examples)("%s has no invented testimonials", (f) => {
    expect(load(f).social_proof.testimonials).toEqual([]);
  });
});

describe("normalizeSpec", () => {
  it("fills Pydantic defaults and the template's default hero model", () => {
    const raw = load("clinic.json");
    delete raw.hero.model;
    delete raw.social_proof;
    delete raw.analytics;
    delete raw.noindex;
    const spec = normalizeSpec(raw);
    expect(spec.hero.model).toBe("tooth");
    expect(spec.social_proof.testimonials).toEqual([]);
    expect(spec.analytics.enabled).toBe(false);
    expect(spec.noindex).toBe(true);
  });
});

describe("JSON-LD", () => {
  it("uses specific @types per template", () => {
    const types = Object.fromEntries(examples.map((f) => [f, schemaType(normalizeSpec(load(f)))]));
    expect(types["clinic.json"]).toBe("Dentist");
    expect(types["restaurant.json"]).toBe("Restaurant");
    expect(types["salon.json"]).toBe("BeautySalon");
    expect(types["fitness.json"]).toBe("HealthClub");
    expect(types["legal-finance.json"]).toBe("AccountingService");
    expect(types["real-estate.json"]).toBe("RealEstateAgent");
    expect(types["home-services.json"]).toBe("HomeAndConstructionBusiness");
    expect(types["generic-premium.json"]).toBe("LocalBusiness");
  });

  it("builds LocalBusiness with NAP, geo, hours, rating and sameAs", () => {
    const spec = normalizeSpec(load("clinic.json"));
    const ld = buildLocalBusinessJsonLd(spec) as Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
    expect(ld.name).toBe("Sample Dental Studio");
    expect(ld.telephone).toBe("+918000000000");
    expect(ld.address.addressLocality).toBe("Bengaluru");
    expect(ld.geo).toEqual({ "@type": "GeoCoordinates", latitude: 12.9719, longitude: 77.6412 });
    expect(ld.openingHoursSpecification).toHaveLength(6);
    expect(ld.aggregateRating).toMatchObject({ ratingValue: 4.8, reviewCount: 212 });
    expect(ld.sameAs).toHaveLength(2);
    expect(buildFaqJsonLd(spec)).not.toBeNull();
  });

  it("omits aggregateRating when the rating is unknown", () => {
    const ld = buildLocalBusinessJsonLd(normalizeSpec(load("home-services.json")));
    expect(ld.aggregateRating).toBeUndefined();
  });

  it("escapes </script> in serialised JSON-LD", () => {
    expect(jsonLdString({ a: "</script><script>alert(1)</script>" })).not.toContain("</script>");
  });
});

describe("formatting", () => {
  it("formats prices per locale and currency", () => {
    expect(formatPrice("150000", "en-IN", "INR")).toBe("₹1,50,000");
    expect(formatPrice("85", "en-US", "USD")).toBe("$85");
    expect(formatPrice("From 180", "en-US", "USD")).toBe("From $180");
    expect(formatPrice("On request", "en-IN", "INR")).toBe("On request");
    expect(formatPrice("₹1,500", "en-IN", "INR")).toBe("₹1,500");
  });

  it("formats times per locale", () => {
    expect(formatTime("19:00", "en-US")).toBe("7:00 PM");
    expect(formatTime("09:30", "en-IN").toLowerCase()).toBe("9:30 am");
  });

  it("handles overnight opening hours", () => {
    const rows = [{ day: "Friday" as const, opens: "19:00", closes: "01:00" }];
    expect(isOpenAt(rows, "Friday", 20 * 60)).toBe(true);
    expect(isOpenAt(rows, "Saturday", 30)).toBe(true);
    expect(isOpenAt(rows, "Saturday", 90)).toBe(false);
    expect(isOpenAt(rows, "Friday", 18 * 60)).toBe(false);
  });

  it("builds absolute URLs under a site_url that includes a sub-path", () => {
    const spec = normalizeSpec({ ...load("clinic.json"), site_url: "https://host.example.com/previews/abc/" });
    expect(absoluteUrl(spec, "/")).toBe("https://host.example.com/previews/abc/");
    expect(absoluteUrl(spec, "/privacy/")).toBe("https://host.example.com/previews/abc/privacy/");
    expect(absoluteUrl(spec, "/og.png")).toBe("https://host.example.com/previews/abc/og.png");
  });
});
