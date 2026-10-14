import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Download, ExternalLink } from "lucide-react";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ScorePill } from "@/components/Score";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { api, download, qs, type TargetsConfig } from "@/lib/api";
import type { LeadPage, LeadRow } from "@/lib/types";

const FILTER_KEYS = [
  "campaign_id",
  "city",
  "category",
  "country",
  "grade",
  "max_score",
  "min_score",
  "has_website",
  "email",
  "status",
  "q",
] as const;

function NotFound({ value }: { value: string }) {
  return value === "not found" ? <span className="text-slate-400 italic">not found</span> : value;
}

function LeadCard({ lead }: { lead: LeadRow }) {
  return (
    <li className="px-4 py-3">
      <Link to={`/leads/${lead.id}`} className="flex items-start gap-3">
        <ScorePill score={lead.score} grade={lead.grade} />
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium">{lead.name}</p>
          <p className="truncate text-xs text-slate-500">
            {lead.category} · {lead.city}
          </p>
          <p className="truncate text-xs text-slate-600">
            <NotFound value={lead.email} /> · {lead.phone}
          </p>
        </div>
        {lead.preview_url && <Badge tone="green">preview</Badge>}
      </Link>
    </li>
  );
}

export function LeadsPage() {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  const page = Number(params.get("page") ?? 1);
  const filters = Object.fromEntries(
    FILTER_KEYS.map((k) => [k, params.get(k) ?? undefined]),
  ) as Record<string, string | undefined>;
  const sort = params.get("sort") ?? "score";

  const targets = useQuery({
    queryKey: ["targets"],
    queryFn: () => api<TargetsConfig>("/api/config/targets"),
  });
  const leads = useQuery({
    queryKey: ["leads", filters, page, sort],
    queryFn: () => api<LeadPage>(`/api/leads${qs({ ...filters, page, sort, page_size: 50 })}`),
    placeholderData: keepPreviousData,
  });

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete("page");
    setParams(next);
  };
  const exportAs = (format: "csv" | "xlsx") =>
    download(`/api/leads/export${qs({ ...filters, format })}`, `leads.${format}`);

  const data = leads.data;
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Leads</h1>
          <p className="text-sm text-slate-600">
            {data ? `${data.total} businesses` : "Loading…"} · lowest scores first
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => exportAs("csv")}>
            <Download className="size-4" aria-hidden /> CSV
          </Button>
          <Button variant="secondary" onClick={() => exportAs("xlsx")}>
            <Download className="size-4" aria-hidden /> Excel
          </Button>
        </div>
      </div>

      <Card className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
        <form
          className="col-span-2"
          onSubmit={(e) => {
            e.preventDefault();
            set("q", q);
          }}
        >
          <label className="sr-only" htmlFor="lead-search">
            Search
          </label>
          <Input
            id="lead-search"
            type="search"
            placeholder="Search name, address, email"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onBlur={() => set("q", q)}
          />
        </form>
        <Select
          aria-label="City"
          value={filters.city ?? ""}
          onChange={(e) => set("city", e.target.value)}
        >
          <option value="">All cities</option>
          {targets.data?.cities.map((c) => (
            <option key={c.id} value={c.name}>
              {c.name}
            </option>
          ))}
        </Select>
        <Select
          aria-label="Category"
          value={filters.category ?? ""}
          onChange={(e) => set("category", e.target.value)}
        >
          <option value="">All categories</option>
          {targets.data?.categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </Select>
        <Select
          aria-label="Grade"
          value={filters.grade ?? ""}
          onChange={(e) => set("grade", e.target.value)}
        >
          <option value="">Any grade</option>
          {["A", "B", "C", "D"].map((g) => (
            <option key={g} value={g}>
              Grade {g}
            </option>
          ))}
        </Select>
        <Select
          aria-label="Website"
          value={filters.has_website ?? ""}
          onChange={(e) => set("has_website", e.target.value)}
        >
          <option value="">With or without site</option>
          <option value="true">Has website</option>
          <option value="false">No website</option>
        </Select>
        <Select
          aria-label="Email"
          value={filters.email ?? ""}
          onChange={(e) => set("email", e.target.value)}
        >
          <option value="">Email: any</option>
          <option value="found">Email found</option>
          <option value="not_found">Email not found</option>
        </Select>
      </Card>

      <Card className="overflow-hidden p-0 sm:p-0">
        {/* Phone: stacked cards. Desktop: table. */}
        <ul className="divide-y divide-slate-100 md:hidden">
          {data?.items.map((lead) => (
            <LeadCard key={lead.id} lead={lead} />
          ))}
        </ul>
        <div className="hidden overflow-x-auto md:block">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500 uppercase">
              <tr>
                <th className="px-4 py-3">
                  <button
                    className="uppercase"
                    onClick={() => set("sort", sort === "score" ? "-score" : "score")}
                  >
                    Score {sort === "score" ? "↑" : sort === "-score" ? "↓" : ""}
                  </button>
                </th>
                <th className="px-4 py-3">Business</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Phone</th>
                <th className="px-4 py-3">Website</th>
                <th className="px-4 py-3">Rating</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.map((lead) => (
                <tr key={lead.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <ScorePill score={lead.score} grade={lead.grade} />
                  </td>
                  <td className="max-w-64 px-4 py-3">
                    <Link className="font-medium hover:underline" to={`/leads/${lead.id}`}>
                      {lead.name}
                    </Link>
                    <div className="truncate text-xs text-slate-500">
                      {lead.category} · {lead.city}, {lead.country}
                    </div>
                  </td>
                  <td
                    className="max-w-56 truncate px-4 py-3"
                    title={lead.email_source_url ?? undefined}
                  >
                    <NotFound value={lead.email} />
                    {lead.email_confidence !== null && (
                      <span className="ml-1 text-xs text-slate-400">
                        {Math.round(lead.email_confidence * 100)}%
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <NotFound value={lead.phone} />
                  </td>
                  <td className="max-w-48 truncate px-4 py-3">
                    {lead.website === "not found" ? (
                      <span className="text-slate-400 italic">none</span>
                    ) : (
                      <a
                        className="inline-flex items-center gap-1 text-brand-700 hover:underline"
                        href={lead.website}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {lead.website.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                        <ExternalLink className="size-3" aria-hidden />
                      </a>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {lead.rating ?? "–"}
                    {lead.review_count !== null && (
                      <span className="text-xs text-slate-500"> ({lead.review_count})</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={lead.preview_url ? "green" : "slate"}>
                      {lead.lead_status.replace("_", " ")}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {data?.items.length === 0 && (
          <p className="p-6 text-sm text-slate-500">No leads match these filters.</p>
        )}
      </Card>

      {pages > 1 && (
        <nav className="flex items-center justify-center gap-3" aria-label="Pagination">
          <Button
            variant="secondary"
            disabled={page <= 1}
            onClick={() => {
              const next = new URLSearchParams(params);
              next.set("page", String(page - 1));
              setParams(next);
            }}
          >
            Previous
          </Button>
          <span className="text-sm text-slate-600">
            Page {page} of {pages}
          </span>
          <Button
            variant="secondary"
            disabled={page >= pages}
            onClick={() => {
              const next = new URLSearchParams(params);
              next.set("page", String(page + 1));
              setParams(next);
            }}
          >
            Next
          </Button>
        </nav>
      )}
    </div>
  );
}
