import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { DraftEditor } from "@/components/DraftEditor";
import { Select } from "@/components/ui/select";
import { api, qs } from "@/lib/api";
import type { Draft } from "@/lib/types";

export function ApprovalsPage() {
  const [status, setStatus] = useState("drafted");
  const [channel, setChannel] = useState("");
  const drafts = useQuery({
    queryKey: ["drafts", status, channel],
    queryFn: () => api<Draft[]>(`/api/drafts${qs({ status, channel, limit: 200 })}`),
  });
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Approvals</h1>
        <p className="text-sm text-slate-600">
          Nothing is sent until you approve it. Approved emails still pass the suppression list, the
          daily limit and the agency details check at send time.
        </p>
      </div>
      <div className="grid max-w-md grid-cols-2 gap-3">
        <Select aria-label="Status" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="drafted">Waiting for approval</option>
          <option value="approved">Approved, not sent</option>
          <option value="sent">Sent</option>
          <option value="replied">Replied</option>
          <option value="cancelled">Rejected or cancelled</option>
        </Select>
        <Select aria-label="Channel" value={channel} onChange={(e) => setChannel(e.target.value)}>
          <option value="">All channels</option>
          <option value="email">Email</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="call_script">Call script</option>
        </Select>
      </div>
      {drafts.data?.length === 0 && <p className="text-sm text-slate-500">Nothing here.</p>}
      <div className="space-y-4">
        {drafts.data?.map((d) => (
          <DraftEditor key={d.id} draft={d} showBusiness />
        ))}
      </div>
    </div>
  );
}
