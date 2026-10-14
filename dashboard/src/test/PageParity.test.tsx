import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PageParityList } from "@/pages/LeadDetailPage";

describe("PageParityList", () => {
  it("lists every current page and flags the missing ones", () => {
    render(
      <PageParityList
        parity={{
          expected: 3,
          present: 2,
          missing: ["/team"],
          pages: [
            {
              path: "/menu.html",
              label: "Menu",
              kind: "menu",
              new_path: "/menu",
              status: "redirect",
              http_status: 200,
            },
            {
              path: "/about",
              label: "About",
              kind: "about",
              new_path: "/about",
              status: "ok",
              http_status: 200,
            },
            {
              path: "/team",
              label: "Team",
              kind: "team",
              new_path: "/team",
              status: "missing",
              http_status: 404,
            },
          ],
        }}
      />,
    );
    expect(screen.getByText("2 of 3 on the new site")).toBeInTheDocument();
    expect(screen.getByText("→ /menu")).toBeInTheDocument();
    expect(screen.getByText("Missing")).toBeInTheDocument();
    expect(screen.getAllByText(/Rebuilt|Redirects/)).toHaveLength(2);
  });
});
