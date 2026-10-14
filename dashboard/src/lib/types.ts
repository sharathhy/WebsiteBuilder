// Shapes returned by the LeadForge API (see api/leadforge/schemas/leads.py).

export type LeadStatus =
  | "new"
  | "enriched"
  | "audited"
  | "rebuild_queued"
  | "site_ready"
  | "contacted"
  | "won"
  | "lost"
  | "suppressed";

export type DraftStatus =
  "drafted" | "approved" | "sent" | "replied" | "won" | "lost" | "cancelled";

export type Channel = "email" | "whatsapp" | "sms" | "call_script";

export interface Campaign {
  id: string;
  name: string;
  status: "draft" | "running" | "paused" | "completed";
  cities: string[];
  categories: string[];
  radius_m: number;
  max_results_per_target: number;
  rebuild_threshold: number;
  created_at: string;
}

export interface CampaignProgress {
  campaign: Campaign;
  jobs: Record<string, Record<string, number>>;
  leads: Record<string, number>;
  total_leads: number;
}

export interface LeadRow {
  id: string;
  name: string;
  category: string;
  city: string;
  state: string | null;
  country: "IN" | "US";
  address: string;
  phone: string;
  email: string;
  email_source_url: string | null;
  email_confidence: number | null;
  website: string;
  maps_url: string | null;
  rating: number | null;
  review_count: number | null;
  score: number | null;
  grade: "A" | "B" | "C" | "D" | null;
  lead_status: LeadStatus;
  has_website: boolean;
  preview_url: string | null;
  places_fetched_at: string | null;
  enriched_at: string | null;
  audited_at: string | null;
}

export interface LeadPage {
  items: LeadRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface Draft {
  id: string;
  business_id: string;
  business_name: string | null;
  to: string | null;
  channel: Channel;
  variant: string;
  subject: string | null;
  body: string;
  status: DraftStatus;
  sequence_day: number;
  scheduled_for: string | null;
  approved_at: string | null;
  sent_at: string | null;
  created_at: string;
  preview_url: string | null;
  score_before: number | null;
  score_after: number | null;
}

export interface Site {
  id: string;
  template: string;
  status: string;
  attempts: number;
  preview_url: string | null;
  score: number | null;
  baseline_score: number | null;
  expires_at: string | null;
  failure_reason: string | null;
  created_at: string;
}

export interface AuditView {
  id: string;
  target_url: string;
  status: "queued" | "running" | "completed" | "failed";
  score: number | null;
  grade: string | null;
  rubric_version: string;
  breakdown: Record<string, { score: number; max: number }>;
  top_issues: string[];
  error: string | null;
  created_at: string;
  generated_site_id: string | null;
  evidence: Record<string, unknown>;
  screenshots: Record<string, string>;
}

export interface ContactView {
  id: string;
  kind: "email" | "phone" | "whatsapp" | "social";
  value: string;
  label: string | null;
  source: string;
  source_url: string | null;
  confidence: number;
  is_role_address: boolean | null;
  mx_valid: boolean | null;
  found_at: string | null;
}

export interface LeadDetail {
  lead: LeadRow;
  business: Record<string, unknown>;
  contacts: ContactView[];
  website: Record<string, unknown> | null;
  audits: AuditView[];
  sites: Site[];
  drafts: Draft[];
  jobs: { id: string; kind: string; status: string; error: string | null; created_at: string }[];
}

export interface Overview {
  funnel: { stage: string; count: number }[];
  leads_by_status: Record<string, number>;
  grades: Record<string, number>;
  sites_by_status: Record<string, number>;
  drafts_by_status: Record<string, number>;
  email_events: Record<string, number>;
  emails_found: number;
  bounces: number;
  avg_score_before: number | null;
  avg_score_after: number | null;
}

export interface ProviderUsage {
  calls: number;
  mocked_calls: number;
  units: number;
  cost_usd: number;
  tokens_in: number;
  tokens_out: number;
  budget_usd: number | null;
  free_quota: number | null;
}

export interface Costs {
  month_start: string;
  budget_usd: number;
  spent_usd: number;
  remaining_usd: number;
  mock_mode: boolean;
  providers: Record<string, ProviderUsage>;
}

export interface Queues {
  counts: Record<string, Record<string, number>>;
  avg_duration_s: Record<string, number>;
  dead_letters: {
    id: string;
    kind: string;
    queue: string;
    error: string | null;
    attempts: number;
    finished_at: string | null;
    business_id: string | null;
  }[];
}

export interface SuppressionEntry {
  id: string;
  email: string | null;
  domain: string | null;
  phone_e164: string | null;
  reason: string;
  source: string | null;
  created_at: string;
}
