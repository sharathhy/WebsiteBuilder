import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, ExternalLink, X } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/select";
import { api } from "@/lib/api";
import type { Draft } from "@/lib/types";

const CHANNEL_LABEL: Record<string, string> = {
  email: "Email",
  whatsapp: "WhatsApp",
  sms: "SMS",
  call_script: "Call script",
};

const statusTone = {
  drafted: "amber",
  approved: "green",
  sent: "green",
  replied: "green",
  won: "green",
  lost: "slate",
  cancelled: "slate",
} as const;

export function DraftEditor({
  draft,
  showBusiness = false,
}: {
  draft: Draft;
  showBusiness?: boolean;
}) {
  const qc = useQueryClient();
  const [subject, setSubject] = useState(draft.subject ?? "");
  const [body, setBody] = useState(draft.body);
  const [copied, setCopied] = useState(false);
  const dirty = body !== draft.body || subject !== (draft.subject ?? "");
  const editable = draft.status === "drafted";
  const isEmail = draft.channel === "email";

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["drafts"] });
    qc.invalidateQueries({ queryKey: ["lead", draft.business_id] });
  };
  const save = useMutation({
    mutationFn: () =>
      api<Draft>(`/api/drafts/${draft.id}`, {
        method: "PATCH",
        body: JSON.stringify(isEmail ? { subject, body } : { body }),
      }),
    onSuccess: (d) => {
      setBody(d.body);
      refresh();
    },
  });
  const approve = useMutation({
    mutationFn: async () => {
      if (dirty) await save.mutateAsync();
      return api<Draft>(`/api/drafts/${draft.id}/approve`, {
        method: "POST",
        body: JSON.stringify({ send_now: isEmail }),
      });
    },
    onSuccess: refresh,
  });
  const reject = useMutation({
    mutationFn: () => api<Draft>(`/api/drafts/${draft.id}/reject`, { method: "POST" }),
    onSuccess: refresh,
  });
  const mark = useMutation({
    mutationFn: (status: string) =>
      api<Draft>(`/api/drafts/${draft.id}/mark`, {
        method: "POST",
        body: JSON.stringify({ status }),
      }),
    onSuccess: refresh,
  });
  const error = save.error ?? approve.error ?? reject.error ?? mark.error;
  const words = body.split(/\s+/).filter(Boolean).length;

  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={statusTone[draft.status]}>{draft.status}</Badge>
        <span className="text-sm font-medium">
          {CHANNEL_LABEL[draft.channel]}
          {isEmail && draft.sequence_day === 0 && ` · variant ${draft.variant}`}
          {draft.sequence_day > 0 && ` · day ${draft.sequence_day} follow-up`}
        </span>
        {showBusiness && (
          <Link
            to={`/leads/${draft.business_id}`}
            className="text-sm text-brand-700 hover:underline"
          >
            {draft.business_name}
          </Link>
        )}
        <span className="ml-auto text-xs text-slate-500">
          to {draft.to ?? <em>no published contact</em>}
        </span>
      </div>
      {draft.preview_url && (
        <p className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
          <a
            className="inline-flex items-center gap-1 text-brand-700 hover:underline"
            href={draft.preview_url}
            target="_blank"
            rel="noreferrer"
          >
            Preview site <ExternalLink className="size-3" aria-hidden />
          </a>
          {draft.score_before !== null && draft.score_after !== null && (
            <span>
              score {draft.score_before} → <strong>{draft.score_after}</strong>
            </span>
          )}
        </p>
      )}
      {isEmail && (
        <label className="block space-y-1 text-sm font-medium">
          Subject
          <Input
            value={subject}
            disabled={!editable}
            onChange={(e) => setSubject(e.target.value)}
          />
        </label>
      )}
      <label className="block space-y-1 text-sm font-medium">
        Message
        <Textarea
          rows={isEmail ? 12 : 8}
          value={body}
          disabled={!editable}
          onChange={(e) => setBody(e.target.value)}
        />
      </label>
      <p className="text-xs text-slate-500">
        {words} words.{" "}
        {isEmail
          ? "The postal address and one-click unsubscribe footer are re-added on send."
          : "Copy and send this yourself, then mark it sent."}
      </p>
      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error.message}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        {editable && (
          <>
            <Button
              onClick={() => approve.mutate()}
              disabled={approve.isPending || (isEmail && !draft.to)}
            >
              <Check className="size-4" aria-hidden />
              {isEmail ? "Approve & send" : "Approve"}
            </Button>
            {dirty && (
              <Button variant="secondary" onClick={() => save.mutate()} disabled={save.isPending}>
                Save edits
              </Button>
            )}
            <Button variant="ghost" onClick={() => reject.mutate()} disabled={reject.isPending}>
              <X className="size-4" aria-hidden /> Reject
            </Button>
          </>
        )}
        {!isEmail && draft.status !== "cancelled" && (
          <Button
            variant="secondary"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(body);
                setCopied(true);
              } catch {
                setCopied(false);
              }
            }}
          >
            <Copy className="size-4" aria-hidden /> {copied ? "Copied" : "Copy"}
          </Button>
        )}
        {!isEmail && draft.status === "approved" && (
          <Button variant="secondary" onClick={() => mark.mutate("sent")}>
            Mark sent
          </Button>
        )}
        {["sent", "replied"].includes(draft.status) && (
          <>
            {draft.status === "sent" && (
              <Button variant="secondary" onClick={() => mark.mutate("replied")}>
                They replied
              </Button>
            )}
            <Button variant="secondary" onClick={() => mark.mutate("won")}>
              Won
            </Button>
            <Button variant="ghost" onClick={() => mark.mutate("lost")}>
              Lost
            </Button>
          </>
        )}
      </div>
    </Card>
  );
}
