import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type Job, type TargetsConfig } from "@/lib/api";
import { useMe } from "@/lib/auth";
import type { Campaign, CampaignProgress } from "@/lib/types";
import { cn } from "@/lib/utils";

const STAGES = ["discover", "enrich", "audit", "generate", "email"] as const;
const STAGE_LABEL: Record<string, string> = {
  discover: "Find",
  enrich: "Contacts",
  audit: "Score",
  generate: "Build site",
  email: "Drafts",
};

function Chip({
  on,
  onClick,
  children,
}: {
  on: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={cn(
        "min-h-11 rounded-full px-3 text-sm ring-1 transition-colors",
        on
          ? "bg-brand-600 text-white ring-brand-600"
          : "bg-white text-slate-700 ring-slate-300 hover:bg-slate-50",
      )}
    >
      {children}
    </button>
  );
}

function NewCampaign({ onCreated }: { onCreated: (c: Campaign) => void }) {
  const targets = useQuery({
    queryKey: ["targets"],
    queryFn: () => api<TargetsConfig>("/api/config/targets"),
  });
  const [name, setName] = useState("");
  const [cities, setCities] = useState<string[]>([]);
  const [cats, setCats] = useState<string[]>([]);
  const [max, setMax] = useState(20);
  const create = useMutation({
    mutationFn: () =>
      api<Campaign>("/api/campaigns", {
        method: "POST",
        body: JSON.stringify({
          name: name || "Untitled campaign",
          cities,
          categories: cats,
          max_results_per_target: max,
        }),
      }),
    onSuccess: (c) => {
      setName("");
      setCities([]);
      setCats([]);
      onCreated(c);
    },
  });
  const toggle = (list: string[], set: (v: string[]) => void, id: string) =>
    set(list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);

  if (!targets.data) return null;
  const searches = cities.length * cats.length;
  return (
    <Card>
      <CardTitle>New campaign</CardTitle>
      <form
        className="mt-4 space-y-5"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <label className="block space-y-1 text-sm font-medium">
          Name
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Dentists Q4" />
        </label>
        <fieldset>
          <legend className="text-sm font-medium">Cities</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {targets.data.cities
              .filter((c) => c.enabled)
              .map((c) => (
                <Chip
                  key={c.id}
                  on={cities.includes(c.id)}
                  onClick={() => toggle(cities, setCities, c.id)}
                >
                  {c.name}
                  <span className="ml-1 text-xs opacity-70">{c.country}</span>
                </Chip>
              ))}
          </div>
        </fieldset>
        <fieldset>
          <legend className="text-sm font-medium">Categories</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {targets.data.categories
              .filter((c) => c.enabled)
              .map((c) => (
                <Chip
                  key={c.id}
                  on={cats.includes(c.id)}
                  onClick={() => toggle(cats, setCats, c.id)}
                >
                  {c.label}
                </Chip>
              ))}
          </div>
        </fieldset>
        <label className="block max-w-xs space-y-1 text-sm font-medium">
          Max results per city × category (1 to 60)
          <Input
            type="number"
            min={1}
            max={60}
            value={max}
            onChange={(e) => setMax(Number(e.target.value))}
          />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={!searches || create.isPending}>
            Create campaign
          </Button>
          <span className="text-sm text-slate-600">
            {searches} searches, up to {searches * max} businesses
          </span>
        </div>
        {create.isError && <p className="text-sm text-red-600">{create.error.message}</p>}
      </form>
    </Card>
  );
}

function Progress({ campaign }: { campaign: Campaign }) {
  const qc = useQueryClient();
  const isAdmin = useMe().data?.role === "admin";
  const progress = useQuery({
    queryKey: ["campaign-progress", campaign.id],
    queryFn: () => api<CampaignProgress>(`/api/campaigns/${campaign.id}/progress`),
    refetchInterval: (q) => {
      const jobs = q.state.data?.jobs ?? {};
      const busy = Object.values(jobs).some((s) => (s.queued ?? 0) + (s.running ?? 0) > 0);
      return busy || campaign.status === "running" ? 3000 : false;
    },
  });
  const run = useMutation({
    mutationFn: () => api<Job[]>(`/api/campaigns/${campaign.id}/run`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["campaigns"] });
      qc.invalidateQueries({ queryKey: ["campaign-progress", campaign.id] });
    },
  });
  const p = progress.data;
  return (
    <Card>
      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-0 flex-1">
          <CardTitle className="truncate">{campaign.name}</CardTitle>
          <p className="text-sm text-slate-600">
            {campaign.cities.join(", ")} · {campaign.categories.join(", ")} · up to{" "}
            {campaign.max_results_per_target} each
          </p>
        </div>
        <Badge tone={campaign.status === "running" ? "amber" : "slate"}>{campaign.status}</Badge>
        {isAdmin && (
          <Button variant="secondary" disabled={run.isPending} onClick={() => run.mutate()}>
            {campaign.status === "draft" ? "Run" : "Run again"}
          </Button>
        )}
      </div>
      {run.isError && <p className="mt-2 text-sm text-red-600">{run.error.message}</p>}
      {p && (
        <>
          <ol className="mt-4 grid grid-cols-5 gap-2 text-center text-xs">
            {STAGES.map((stage) => {
              const s = p.jobs[stage] ?? {};
              const done = s.succeeded ?? 0;
              const pending = (s.queued ?? 0) + (s.running ?? 0) + (s.failed ?? 0);
              const dead = s.dead ?? 0;
              return (
                <li key={stage} className="rounded-lg bg-slate-50 p-2">
                  <div className="font-medium text-slate-700">{STAGE_LABEL[stage]}</div>
                  <div className="mt-1 text-lg font-semibold tabular-nums">{done}</div>
                  {pending > 0 && <div className="text-amber-700">{pending} pending</div>}
                  {dead > 0 && <div className="text-red-700">{dead} failed</div>}
                </li>
              );
            })}
          </ol>
          <p className="mt-3 text-sm">
            <Link
              className="font-medium text-brand-700 underline-offset-2 hover:underline"
              to={`/leads?campaign_id=${campaign.id}`}
            >
              {p.total_leads} leads
            </Link>
            {Object.entries(p.leads).map(([k, v]) => (
              <span key={k} className="ml-2 text-slate-500">
                {k.replace("_", " ")}: {v}
              </span>
            ))}
          </p>
        </>
      )}
    </Card>
  );
}

export function CampaignsPage() {
  const qc = useQueryClient();
  const isAdmin = useMe().data?.role === "admin";
  const campaigns = useQuery({
    queryKey: ["campaigns"],
    queryFn: () => api<Campaign[]>("/api/campaigns"),
  });
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Campaigns</h1>
        <p className="text-sm text-slate-600">
          Each run searches Google Places for every city × category, then finds contacts, scores
          websites and builds previews for the weakest ones.
        </p>
      </div>
      {isAdmin && (
        <NewCampaign onCreated={() => qc.invalidateQueries({ queryKey: ["campaigns"] })} />
      )}
      {campaigns.data?.length === 0 && <p className="text-sm text-slate-500">No campaigns yet.</p>}
      <div className="space-y-4">
        {campaigns.data?.map((c) => (
          <Progress key={c.id} campaign={c} />
        ))}
      </div>
    </div>
  );
}
