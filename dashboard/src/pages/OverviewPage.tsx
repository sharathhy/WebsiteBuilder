import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { api, type Job, type Readiness } from "@/lib/api";
import { useMe } from "@/lib/auth";

const statusTone = {
  queued: "slate",
  running: "amber",
  succeeded: "green",
  failed: "amber",
  dead: "red",
} as const;

export function OverviewPage() {
  const qc = useQueryClient();
  const me = useMe();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<Readiness>("/health/ready"),
    refetchInterval: 10_000,
  });
  const jobs = useQuery({
    queryKey: ["jobs"],
    queryFn: () => api<Job[]>("/api/jobs?limit=20"),
    refetchInterval: 3_000,
  });
  const ping = useMutation({
    mutationFn: () => api<Job>("/api/jobs/ping", { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardTitle>System health</CardTitle>
          <ul className="mt-3 space-y-2 text-sm">
            {health.data ? (
              Object.entries(health.data.checks).map(([name, value]) => (
                <li key={name} className="flex items-center justify-between">
                  <span className="capitalize">{name}</span>
                  <Badge tone={value.startsWith("ok") ? "green" : "red"}>{value}</Badge>
                </li>
              ))
            ) : (
              <li className="text-slate-500">{health.isError ? "API unreachable" : "Checking…"}</li>
            )}
          </ul>
        </Card>
        <Card>
          <CardTitle>Queue check</CardTitle>
          <p className="mt-2 text-sm text-slate-600">
            {health.data?.mode === "local"
              ? "Sends a no-op job through the API and the in-process job runner, and records it in the local database."
              : "Sends a no-op job through the API, Redis and a worker, and records it in Postgres."}
          </p>
          <Button
            className="mt-4 w-full sm:w-auto"
            onClick={() => ping.mutate()}
            disabled={ping.isPending || me.data?.role !== "admin"}
          >
            Run test job
          </Button>
          {ping.isError && <p className="mt-2 text-sm text-red-600">{ping.error.message}</p>}
        </Card>
      </div>
      <Card className="p-0 sm:p-0">
        <div className="p-4 sm:p-6">
          <CardTitle>Recent jobs</CardTitle>
        </div>
        {jobs.data?.length ? (
          <ul className="divide-y divide-slate-100">
            {jobs.data.map((job) => (
              <li
                key={job.id}
                className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 sm:px-6"
              >
                <Badge tone={statusTone[job.status]}>{job.status}</Badge>
                <span className="text-sm font-medium">{job.kind}</span>
                <span className="text-xs text-slate-500">{job.queue} queue</span>
                <span className="ml-auto text-xs text-slate-500">
                  {new Date(job.created_at).toLocaleString()}
                </span>
                {job.error && <p className="w-full text-xs text-red-600">{job.error}</p>}
              </li>
            ))}
          </ul>
        ) : (
          <p className="px-4 pb-6 text-sm text-slate-500 sm:px-6">No jobs yet.</p>
        )}
      </Card>
    </div>
  );
}
