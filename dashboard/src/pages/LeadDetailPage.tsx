import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { DraftEditor } from "@/components/DraftEditor";
import { Bar, ScorePill } from "@/components/Score";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { api, type Job } from "@/lib/api";
import type { AuditView, LeadDetail } from "@/lib/types";
import { CATEGORY_LABELS, cn } from "@/lib/utils";

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="text-sm break-words">{children}</dd>
    </div>
  );
}

function Breakdown({ audit }: { audit: AuditView }) {
  return (
    <ul className="space-y-2">
      {Object.entries(audit.breakdown).map(([cat, { score, max }]) => (
        <li key={cat} className="grid grid-cols-[8rem_1fr_3.5rem] items-center gap-3 text-sm">
          <span className="truncate">{CATEGORY_LABELS[cat] ?? cat}</span>
          <Bar value={score} max={max} />
          <span className="text-right tabular-nums">
            {score}/{max}
          </span>
        </li>
      ))}
    </ul>
  );
}

export function LeadDetailPage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const [viewport, setViewport] = useState<"mobile" | "desktop">("mobile");
  const detail = useQuery({
    queryKey: ["lead", id],
    queryFn: () => api<LeadDetail>(`/api/leads/${id}`),
    refetchInterval: (q) =>
      q.state.data?.jobs.some((j) => j.status === "queued" || j.status === "running")
        ? 3000
        : false,
  });
  const action = useMutation({
    mutationFn: (kind: "reaudit" | "regenerate") =>
      api<Job>(`/api/leads/${id}/${kind}`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lead", id] }),
  });

  const d = detail.data;
  if (detail.isError) return <p className="text-sm text-red-600">{detail.error.message}</p>;
  if (!d) return <p className="text-sm text-slate-500">Loading…</p>;
  const lead = d.lead;
  const original = d.audits.find((a) => !a.generated_site_id && a.status === "completed");
  const failed = d.audits.find((a) => !a.generated_site_id && a.status === "failed");
  const site = d.sites[0];
  const siteAudit = site ? d.audits.find((a) => a.generated_site_id === site.id) : undefined;

  return (
    <div className="space-y-6">
      <Link to="/leads" className="inline-flex min-h-11 items-center gap-1 text-sm text-slate-600">
        <ArrowLeft className="size-4" aria-hidden /> Leads
      </Link>
      <div className="flex flex-wrap items-start gap-4">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold tracking-tight">{lead.name}</h1>
          <p className="text-sm text-slate-600">
            {lead.category} · {lead.address}
          </p>
        </div>
        <ScorePill score={lead.score} grade={lead.grade} />
        <Badge>{lead.lead_status.replace("_", " ")}</Badge>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardTitle>Business</CardTitle>
          <dl className="mt-3 grid gap-3">
            <Fact label="Phone">{lead.phone}</Fact>
            <Fact label="Email">
              {lead.email}
              {lead.email_source_url && (
                <a
                  className="ml-1 text-xs text-brand-700 hover:underline"
                  href={lead.email_source_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  (source)
                </a>
              )}
            </Fact>
            <Fact label="Website">
              {lead.has_website ? (
                <a
                  className="text-brand-700 hover:underline"
                  href={lead.website}
                  target="_blank"
                  rel="noreferrer"
                >
                  {lead.website}
                </a>
              ) : (
                "No website"
              )}
            </Fact>
            <Fact label="Google rating">
              {lead.rating ?? "–"} ({lead.review_count ?? 0} reviews)
            </Fact>
            {lead.maps_url && (
              <Fact label="Maps">
                <a
                  className="text-brand-700 hover:underline"
                  href={lead.maps_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open in Google Maps
                </a>
              </Fact>
            )}
          </dl>
          <h3 className="mt-5 text-sm font-semibold">Contacts found</h3>
          {d.contacts.length === 0 ? (
            <p className="mt-1 text-sm text-slate-500">None published.</p>
          ) : (
            <ul className="mt-2 space-y-2 text-sm">
              {d.contacts.map((c) => (
                <li key={c.id} className="break-words">
                  <Badge className="mr-1">{c.kind}</Badge>
                  {c.value}
                  <span className="block text-xs text-slate-500">
                    {c.source.replace("_", " ")}
                    {c.kind === "email" && ` · ${Math.round(c.confidence * 100)}% confidence`}
                    {c.is_role_address && " · role address"}
                    {c.source_url && (
                      <>
                        {" · "}
                        <a
                          className="text-brand-700 hover:underline"
                          href={c.source_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          found here
                        </a>
                      </>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="lg:col-span-2">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="mr-auto">Website score</CardTitle>
            <Button
              variant="secondary"
              onClick={() => action.mutate("reaudit")}
              disabled={action.isPending}
            >
              Re-score
            </Button>
          </div>
          {action.isError && <p className="mt-2 text-sm text-red-600">{action.error.message}</p>}
          {!lead.has_website && (
            <p className="mt-3 text-sm text-slate-600">
              No website listed on Google. Scored 0, so it went straight to the rebuild queue.
            </p>
          )}
          {failed && !original && (
            <p className="mt-3 text-sm text-amber-700">
              Could not score: {failed.error}. Bot-protected sites are skipped, never bypassed.
            </p>
          )}
          {original && (
            <div className="mt-4 grid gap-6 md:grid-cols-2">
              <Breakdown audit={original} />
              <div>
                <h3 className="text-sm font-semibold">Top issues</h3>
                <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm">
                  {original.top_issues.map((i) => (
                    <li key={i}>{i}</li>
                  ))}
                </ol>
              </div>
            </div>
          )}
          {original && Object.keys(original.screenshots).length > 0 && (
            <div className="mt-4 flex gap-3 overflow-x-auto">
              {Object.entries(original.screenshots).map(([name, url]) => (
                <a key={name} href={url} target="_blank" rel="noreferrer" className="shrink-0">
                  <img
                    src={url}
                    alt={`Current site, ${name.replace("_", " ")}`}
                    loading="lazy"
                    className={cn(
                      "rounded-lg object-cover object-top ring-1 ring-slate-200",
                      name.startsWith("mobile") ? "h-64 w-32" : "h-64 w-96",
                    )}
                  />
                </a>
              ))}
            </div>
          )}
        </Card>
      </div>

      {site && (
        <Card>
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="mr-auto">New site preview</CardTitle>
            <Badge
              tone={
                site.status === "live"
                  ? "green"
                  : site.status === "manual_review"
                    ? "amber"
                    : "slate"
              }
            >
              {site.status.replace("_", " ")}
            </Badge>
            {site.baseline_score !== null && site.score !== null && (
              <span className="text-sm">
                {site.baseline_score} → <strong className="text-emerald-700">{site.score}</strong>
              </span>
            )}
            <Button
              variant="secondary"
              onClick={() => action.mutate("regenerate")}
              disabled={action.isPending}
            >
              Regenerate
            </Button>
          </div>
          {site.failure_reason && (
            <p className="mt-2 text-sm text-amber-700">{site.failure_reason}</p>
          )}
          {site.preview_url && (
            <>
              <div className="mt-3 flex items-center gap-2">
                <div
                  className="inline-flex rounded-lg bg-slate-100 p-1"
                  role="group"
                  aria-label="Viewport"
                >
                  {(["mobile", "desktop"] as const).map((v) => (
                    <button
                      key={v}
                      aria-pressed={viewport === v}
                      onClick={() => setViewport(v)}
                      className={cn(
                        "min-h-9 rounded-md px-3 text-sm capitalize",
                        viewport === v ? "bg-white shadow-sm" : "text-slate-600",
                      )}
                    >
                      {v}
                    </button>
                  ))}
                </div>
                <a
                  className="ml-auto inline-flex min-h-11 items-center gap-1 text-sm text-brand-700 hover:underline"
                  href={site.preview_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open <ExternalLink className="size-3" aria-hidden />
                </a>
              </div>
              <div className="mt-3 overflow-hidden rounded-lg bg-slate-100 p-2">
                <iframe
                  title="Generated site preview"
                  src={site.preview_url}
                  className={cn(
                    "mx-auto h-[640px] rounded-md bg-white ring-1 ring-slate-200",
                    viewport === "mobile" ? "w-[390px] max-w-full" : "w-full",
                  )}
                  sandbox="allow-scripts allow-forms allow-popups"
                />
              </div>
            </>
          )}
          {siteAudit && (
            <div className="mt-4">
              <h3 className="mb-2 text-sm font-semibold">Preview score breakdown</h3>
              <Breakdown audit={siteAudit} />
            </div>
          )}
        </Card>
      )}

      {d.drafts.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">Outreach</h2>
          {d.drafts.map((draft) => (
            <DraftEditor key={draft.id} draft={draft} />
          ))}
        </section>
      )}

      <Card>
        <CardTitle>Activity</CardTitle>
        <ul className="mt-3 divide-y divide-slate-100 text-sm">
          {d.jobs.map((j) => (
            <li key={j.id} className="flex flex-wrap items-center gap-2 py-2">
              <Badge
                tone={j.status === "succeeded" ? "green" : j.status === "dead" ? "red" : "amber"}
              >
                {j.status}
              </Badge>
              <span>{j.kind}</span>
              <span className="ml-auto text-xs text-slate-500">
                {new Date(j.created_at).toLocaleString()}
              </span>
              {j.error && <p className="w-full text-xs text-red-600">{j.error}</p>}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
