import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, tokens, type User } from "./api";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/api/auth/me"),
    enabled: Boolean(tokens.access),
    retry: false,
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return () => {
    tokens.clear();
    qc.clear();
    window.location.assign("/login");
  };
}
