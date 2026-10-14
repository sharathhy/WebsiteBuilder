// Thin fetch wrapper: attaches the access token and refreshes it once on 401.

export type Role = "admin" | "reviewer";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface Job {
  id: string;
  queue: string;
  kind: string;
  status: "queued" | "running" | "succeeded" | "failed" | "dead";
  attempts: number;
  max_attempts: number;
  error: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface City {
  id: string;
  name: string;
  state: string;
  country: "IN" | "US";
  lat: number;
  lng: number;
  enabled: boolean;
  metro?: string;
}

export interface Category {
  id: string;
  label: string;
  query: string;
  template: string;
  enabled: boolean;
}

export interface TargetsConfig {
  defaults: {
    radius_m: number;
    max_results_per_target: number;
    rebuild_threshold: number;
    audit_cache_days: number;
    places_refresh_days: number;
  };
  cities: City[];
  categories: Category[];
}

export interface Readiness {
  status: "ok" | "degraded";
  checks: Record<string, string>;
}

const ACCESS = "lf.access";
const REFRESH = "lf.refresh";

// Storage can throw (private mode, blocked site data); auth then lasts for the tab only.
const memory = new Map<string, string>();
function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return memory.get(key) ?? null;
  }
}
function write(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    if (value === null) memory.delete(key);
    else memory.set(key, value);
  }
}

export const tokens = {
  get access() {
    return read(ACCESS);
  },
  set(access: string, refresh: string) {
    write(ACCESS, access);
    write(REFRESH, refresh);
  },
  clear() {
    write(ACCESS, null);
    write(REFRESH, null);
  },
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function tryRefresh(): Promise<boolean> {
  const refresh = read(REFRESH);
  if (!refresh) return false;
  const res = await fetch("/api/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) return false;
  const body = await res.json();
  tokens.set(body.access_token, body.refresh_token);
  return true;
}

export async function api<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  const access = tokens.access;
  if (access) headers.set("Authorization", `Bearer ${access}`);
  if (init.body && !(init.body instanceof URLSearchParams)) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(path, { ...init, headers });
  if (res.status === 401 && retry && (await tryRefresh())) {
    return api<T>(path, init, false);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* non-JSON error body */
    }
    if (res.status === 401) tokens.clear();
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export async function login(email: string, password: string): Promise<void> {
  const body = await api<{ access_token: string; refresh_token: string }>(
    "/api/auth/login",
    { method: "POST", body: new URLSearchParams({ username: email, password }) },
    false,
  );
  tokens.set(body.access_token, body.refresh_token);
}
