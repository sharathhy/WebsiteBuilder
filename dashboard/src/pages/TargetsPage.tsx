import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type TargetsConfig } from "@/lib/api";
import { useMe } from "@/lib/auth";

export function TargetsPage() {
  const qc = useQueryClient();
  const isAdmin = useMe().data?.role === "admin";
  const query = useQuery({
    queryKey: ["targets"],
    queryFn: () => api<TargetsConfig>("/api/config/targets"),
  });
  const [draft, setDraft] = useState<TargetsConfig | null>(null);
  const config = draft ?? query.data;

  const save = useMutation({
    mutationFn: (body: TargetsConfig) =>
      api<TargetsConfig>("/api/config/targets", { method: "PUT", body: JSON.stringify(body) }),
    onSuccess: (data) => {
      qc.setQueryData(["targets"], data);
      setDraft(null);
    },
  });

  if (!config) return <p className="text-sm text-slate-500">Loading targets…</p>;

  const update = (fn: (c: TargetsConfig) => TargetsConfig) => setDraft(fn(structuredClone(config)));
  const enabledCities = config.cities.filter((c) => c.enabled).length;
  const enabledCats = config.categories.filter((c) => c.enabled).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Targets</h1>
          <p className="text-sm text-slate-600">
            {enabledCities} cities × {enabledCats} categories = {enabledCities * enabledCats}{" "}
            searches, up to {config.defaults.max_results_per_target} results each.
          </p>
        </div>
        {isAdmin && (
          <div className="flex gap-2">
            {draft && (
              <Button variant="secondary" onClick={() => setDraft(null)}>
                Discard
              </Button>
            )}
            <Button disabled={!draft || save.isPending} onClick={() => draft && save.mutate(draft)}>
              {save.isPending ? "Saving…" : "Save changes"}
            </Button>
          </div>
        )}
      </div>
      {save.isError && <p className="text-sm text-red-600">{save.error.message}</p>}

      <Card>
        <CardTitle>Defaults</CardTitle>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          {(
            [
              ["radius_m", "Search radius (m)"],
              ["max_results_per_target", "Max results per city × category"],
              ["rebuild_threshold", "Rebuild below score"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="block space-y-1">
              <span className="text-sm font-medium">{label}</span>
              <Input
                type="number"
                disabled={!isAdmin}
                value={config.defaults[key]}
                onChange={(e) =>
                  update((c) => ({
                    ...c,
                    defaults: { ...c.defaults, [key]: Number(e.target.value) },
                  }))
                }
              />
            </label>
          ))}
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <ToggleList
          title="Cities"
          disabled={!isAdmin}
          items={config.cities.map((c) => ({
            id: c.id,
            label: c.name,
            hint: `${c.metro ? `${c.metro}, ` : ""}${c.state}, ${c.country}`,
            enabled: c.enabled,
          }))}
          onToggle={(id) =>
            update((c) => ({
              ...c,
              cities: c.cities.map((x) => (x.id === id ? { ...x, enabled: !x.enabled } : x)),
            }))
          }
        />
        <ToggleList
          title="Categories"
          disabled={!isAdmin}
          items={config.categories.map((c) => ({
            id: c.id,
            label: c.label,
            hint: `“${c.query}” · ${c.template} template`,
            enabled: c.enabled,
          }))}
          onToggle={(id) =>
            update((c) => ({
              ...c,
              categories: c.categories.map((x) =>
                x.id === id ? { ...x, enabled: !x.enabled } : x,
              ),
            }))
          }
        />
      </div>
    </div>
  );
}

function ToggleList(props: {
  title: string;
  disabled: boolean;
  items: { id: string; label: string; hint: string; enabled: boolean }[];
  onToggle: (id: string) => void;
}) {
  return (
    <Card className="p-0 sm:p-0">
      <div className="p-4 sm:p-6">
        <CardTitle>{props.title}</CardTitle>
      </div>
      <ul className="divide-y divide-slate-100">
        {props.items.map((item) => (
          <li key={item.id}>
            <label className="flex min-h-12 cursor-pointer items-center gap-3 px-4 py-2 sm:px-6">
              <input
                type="checkbox"
                className="size-5 accent-brand-600"
                checked={item.enabled}
                disabled={props.disabled}
                onChange={() => props.onToggle(item.id)}
              />
              <span className="text-sm font-medium">{item.label}</span>
              <span className="ml-auto truncate text-xs text-slate-500">{item.hint}</span>
            </label>
          </li>
        ))}
      </ul>
    </Card>
  );
}
