import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { tokens } from "@/lib/api";
import { useMe } from "@/lib/auth";

export function RequireAuth({ children }: { children: ReactNode }) {
  const location = useLocation();
  const me = useMe();
  if (!tokens.access || me.isError) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (me.isPending) {
    return <p className="p-6 text-sm text-slate-500">Loading…</p>;
  }
  return <>{children}</>;
}
