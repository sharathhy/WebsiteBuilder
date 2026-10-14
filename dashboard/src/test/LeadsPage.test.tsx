import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { LeadRow } from "@/lib/types";
import { LeadsPage } from "@/pages/LeadsPage";
import { mockFetch, renderWithProviders } from "./render";

const lead: LeadRow = {
  id: "1",
  name: "Sample Smile Dental 01 Austin",
  category: "dentists",
  city: "Austin",
  state: "TX",
  country: "US",
  address: "1 Sample St",
  phone: "+15125550101",
  email: "not found",
  email_source_url: null,
  email_confidence: null,
  website: "not found",
  maps_url: null,
  rating: 4.5,
  review_count: 12,
  score: 0,
  grade: "D",
  lead_status: "site_ready",
  has_website: false,
  preview_url: "http://localhost:8000/previews/x/",
  places_fetched_at: null,
  enriched_at: null,
  audited_at: null,
};

afterEach(() => vi.restoreAllMocks());

describe("LeadsPage", () => {
  it("lists leads and shows missing values as not found", async () => {
    const { fn, calls } = mockFetch({
      "/api/config/targets": { defaults: {}, cities: [], categories: [] },
      "/api/leads": { items: [lead], total: 1, page: 1, page_size: 50 },
    });
    vi.spyOn(globalThis, "fetch").mockImplementation(fn);
    renderWithProviders(<LeadsPage />, "/leads?grade=D");
    expect((await screen.findAllByText("Sample Smile Dental 01 Austin")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("not found").length).toBeGreaterThan(0);
    expect(screen.getByText(/1 businesses/)).toBeInTheDocument();
    expect(calls.some((c) => c.url.includes("grade=D"))).toBe(true);
  });
});
