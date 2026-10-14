import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bar } from "@/components/Score";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { api, type Job } from "@/lib/api";
import { useMe } from "@/lib/auth";
import type { Costs, Overview, Queues } from "@/lib/types";

const usd = (n: number) => `$${n.toFixed(2)}`;
const PROVIDER_LABEL: Record<string, string> = {
  google_places: "Google Places",
  pagespeed: "PageSpeed Insights",
  anthropic: "Claude",
  vercel: "Vercel",
  resend: "Resend",
  higgsfield: "Higgsfield",
  unsplash: "Unsplash",
};

export function AnalyticsPage() {
  const qc = useQueryClient();
  const isAdmin = useMe().data?.role === "admin";
  const overview = useQuery({
    queryKey: ["analytics", "overview"],
    queryFn: () => api<Overview>("/api/analytics/overview"),
  });
  const costs = useQuery({
    queryKey: ["analytics", "costs"],
    queryFn: () => api<Costs>("/api/analytics/costs"),
  });
  const queues = useQuery({
    queryKey: ["analytics", "queues"],
    queryFn: () => api<Queues>("/api/analytics/queues"),
    refetchInterval: 10_000,
  });
  const retry = useMutation({
    mutationFn: (id: string) => api<Job>(`/api/jobs/${id}/retry`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analytics", "queues"] }),
  });

  const funnel = overview.data?.funnel ?? [];
  const top = Math.max(1, ...funnel.map((f) => f.count));
  const c = costs.data;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardTitle>Funnel</CardTitle>
          <ul className="mt-4 space-y-3">
            {funnel.map((f) => (
              <li
                key={f.stage}
                className="grid grid-cols-[7rem_1fr_3rem] items-center gap-3 text-sm"
              >
                <span>{f.stage}</span>
                <div className="h-6 overflow-hidden rounded bg-slate-100">
                  <div
                    className="h-full rounded bg-brand-600"
                    style={{ width: `${(f.count / top) * 100}%` }}
                  />
                </div>
                <span className="text-right font-semibold tabular-nums">{f.count}</span>
              </li>
            ))}
          </ul>
          {overview.data && (
            <dl className="mt-5 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
              <div>
                <dt className="text-xs text-slate-500">Emails found</dt>
                <dd className="font-semibold">{overview.data.emails_found}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Bounces</dt>
                <dd className="font-semibold">{overview.data.bounces}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Avg score before</dt>
                <dd className="font-semibold">{overview.data.avg_score_before ?? "–"}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Avg preview score</dt>
                <dd className="font-semibold">{overview.data.avg_score_after ?? "–"}</dd>
              </div>
            </dl>
          )}
        </Card>

        <Card>
          <div className="flex items-center gap-2">
            <CardTitle className="mr-auto">Spend this month</CardTitle>
            {c?.mock_mode && <Badge tone="amber">mock mode: no paid calls</Badge>}
          </div>
          {c && (
            <>
              <p className="mt-3 text-3xl font-semibold tabular-nums">
                {usd(c.spent_usd)}
                <span className="text-base font-normal text-slate-500">
                  {" "}
                  of {usd(c.budget_usd)} cap
                </span>
              </p>
              <Bar className="mt-2 h-3" value={c.budget_usd - c.spent_usd} max={c.budget_usd} />
              <p className="mt-1 text-xs text-slate-500">
                Paid calls stop automatically at the cap. Change it in config/agency.yaml.
              </p>
              <table className="mt-4 w-full text-sm">
                <thead className="text-left text-xs text-slate-500">
                  <tr>
                    <th className="py-1 font-normal">Provider</th>
                    <th className="py-1 text-right font-normal">Live calls</th>
                    <th className="py-1 text-right font-normal">Mocked</th>
                    <th className="py-1 text-right font-normal">Cost</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {Object.entries(c.providers).map(([name, p]) => (
                    <tr key={name}>
                      <td className="py-2">{PROVIDER_LABEL[name] ?? name}</td>
                      <td className="py-2 text-right tabular-nums">{p.calls}</td>
                      <td className="py-2 text-right tabular-nums">{p.mocked_calls}</td>
                      <td className="py-2 text-right tabular-nums">{usd(p.cost_usd)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </Card>
      </div>

      <Card>
        <CardTitle>Queues</CardTitle>
        {queues.data && (
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {Object.entries(queues.data.counts).map(([q, s]) => (
              <div key={q} className="rounded-lg bg-slate-50 p-3 text-sm">
                <div className="font-medium capitalize">{q}</div>
                {Object.entries(s).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs text-slate-600">
                    <span>{k}</span>
                    <span className="tabular-nums">{v}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
        <h3 className="mt-5 text-sm font-semibold">Failed jobs (dead letters)</h3>
        {queues.data?.dead_letters.length === 0 ? (
          <p className="mt-1 text-sm text-slate-500">None.</p>
        ) : (
          <ul className="mt-2 divide-y divide-slate-100 text-sm">
            {queues.data?.dead_letters.map((j) => (
              <li key={j.id} className="flex flex-wrap items-center gap-2 py-2">
                <Badge tone="red">{j.kind}</Badge>
                <span className="min-w-0 flex-1 truncate text-xs text-red-700">{j.error}</span>
                {isAdmin && (
                  <Button
                    variant="secondary"
                    onClick={() => retry.mutate(j.id)}
                    disabled={retry.isPending}
                  >
                    Retry
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
