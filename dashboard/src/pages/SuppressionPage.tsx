import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useMe } from "@/lib/auth";
import type { SuppressionEntry } from "@/lib/types";

export function SuppressionPage() {
  const qc = useQueryClient();
  const isAdmin = useMe().data?.role === "admin";
  const [value, setValue] = useState("");
  const entries = useQuery({
    queryKey: ["suppression"],
    queryFn: () => api<SuppressionEntry[]>("/api/suppression"),
  });
  const add = useMutation({
    mutationFn: () => {
      const v = value.trim().toLowerCase();
      const body = v.includes("@")
        ? { email: v }
        : /^[+\d][\d\s().-]+$/.test(v)
          ? { phone: v }
          : {
              domain: v
                .replace(/^https?:\/\//, "")
                .replace(/^www\./, "")
                .split("/")[0],
            };
      return api<SuppressionEntry>("/api/suppression", {
        method: "POST",
        body: JSON.stringify({ ...body, reason: "manual" }),
      });
    },
    onSuccess: () => {
      setValue("");
      qc.invalidateQueries({ queryKey: ["suppression"] });
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => api<void>(`/api/suppression/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["suppression"] }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Do not contact</h1>
        <p className="text-sm text-slate-600">
          Unsubscribes, bounces and complaints land here automatically. Anyone listed is never
          emailed again, and their pending drafts are cancelled.
        </p>
      </div>
      <Card>
        <CardTitle>Add an email, domain or phone</CardTitle>
        <form
          className="mt-3 flex flex-col gap-2 sm:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            if (value.trim()) add.mutate();
          }}
        >
          <label className="sr-only" htmlFor="suppress-value">
            Email, domain or phone
          </label>
          <Input
            id="suppress-value"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="owner@business.com, business.com or +1 512 555 0100"
          />
          <Button type="submit" disabled={add.isPending}>
            Add
          </Button>
        </form>
        {add.isError && <p className="mt-2 text-sm text-red-600">{add.error.message}</p>}
      </Card>
      <Card className="p-0 sm:p-0">
        <ul className="divide-y divide-slate-100 text-sm">
          {entries.data?.map((e) => (
            <li key={e.id} className="flex flex-wrap items-center gap-2 px-4 py-3 sm:px-6">
              <span className="font-medium break-all">{e.email ?? e.domain ?? e.phone_e164}</span>
              <span className="text-xs text-slate-500">{e.reason}</span>
              <span className="ml-auto text-xs text-slate-500">
                {new Date(e.created_at).toLocaleDateString()}
              </span>
              {isAdmin && (
                <button
                  className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100"
                  aria-label={`Remove ${e.email ?? e.domain ?? e.phone_e164}`}
                  onClick={() => remove.mutate(e.id)}
                >
                  <Trash2 className="size-4" />
                </button>
              )}
            </li>
          ))}
          {entries.data?.length === 0 && <li className="px-6 py-4 text-slate-500">Nobody yet.</li>}
        </ul>
      </Card>
    </div>
  );
}
