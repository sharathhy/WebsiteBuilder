import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DraftEditor } from "@/components/DraftEditor";
import type { Draft } from "@/lib/types";
import { mockFetch, renderWithProviders } from "./render";

const draft: Draft = {
  id: "d1",
  business_id: "b1",
  business_name: "Sample Clinic",
  to: "info@sample.example",
  channel: "email",
  variant: "A",
  subject: "Quick idea for Sample Clinic",
  body: "Hi, I built a free preview.",
  status: "drafted",
  sequence_day: 0,
  scheduled_for: null,
  approved_at: null,
  sent_at: null,
  created_at: "2026-10-14T00:00:00Z",
  preview_url: "http://localhost:8000/previews/x/",
  score_before: 12,
  score_after: 93,
};

afterEach(() => vi.restoreAllMocks());

describe("DraftEditor", () => {
  it("only sends after the reviewer clicks Approve & send", async () => {
    const { fn, calls } = mockFetch({ "/api/drafts/d1": { ...draft, status: "approved" } });
    vi.spyOn(globalThis, "fetch").mockImplementation(fn);
    renderWithProviders(<DraftEditor draft={draft} />);
    expect(calls).toHaveLength(0);
    expect(screen.getByText("93")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Approve & send/ }));
    await vi.waitFor(() => expect(calls.at(-1)?.url).toBe("/api/drafts/d1/approve"));
    expect(JSON.parse(String(calls.at(-1)?.init?.body))).toEqual({ send_now: true });
  });

  it("saves edits before approving", async () => {
    const { fn, calls } = mockFetch({ "/api/drafts/d1": draft });
    vi.spyOn(globalThis, "fetch").mockImplementation(fn);
    renderWithProviders(<DraftEditor draft={draft} />);
    await userEvent.type(screen.getByLabelText("Message"), " Thanks!");
    await userEvent.click(screen.getByRole("button", { name: /Approve & send/ }));
    await vi.waitFor(() => expect(calls.map((c) => c.url)).toContain("/api/drafts/d1/approve"));
    expect(calls[0].init?.method).toBe("PATCH");
  });

  it("cannot approve an email with no published address", () => {
    renderWithProviders(<DraftEditor draft={{ ...draft, to: null }} />);
    expect(screen.getByRole("button", { name: /Approve & send/ })).toBeDisabled();
  });
});
