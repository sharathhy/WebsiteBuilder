import { Activity, LogOut, MapPinned } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useLogout, useMe } from "@/lib/auth";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Overview", icon: Activity },
  { to: "/targets", label: "Targets", icon: MapPinned },
];

export function Layout() {
  const me = useMe();
  const logout = useLogout();
  return (
    <div className="min-h-dvh pb-20 sm:pb-0">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4">
          <span className="font-semibold tracking-tight">LeadForge</span>
          <nav className="hidden gap-1 sm:flex" aria-label="Main">
            {NAV.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end
                className={({ isActive }) =>
                  cn(
                    "rounded-md px-3 py-2 text-sm",
                    isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100",
                  )
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2 text-sm text-slate-600">
            <span className="hidden sm:inline">{me.data?.email}</span>
            <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">{me.data?.role}</span>
            <button
              onClick={logout}
              className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-md hover:bg-slate-100"
              aria-label="Sign out"
            >
              <LogOut className="size-4" />
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
      {/* Mobile bottom navigation */}
      <nav
        aria-label="Main"
        className="fixed inset-x-0 bottom-0 grid grid-cols-2 border-t border-slate-200 bg-white sm:hidden"
      >
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end
            className={({ isActive }) =>
              cn(
                "flex min-h-14 flex-col items-center justify-center gap-0.5 text-xs",
                isActive ? "text-brand-700" : "text-slate-500",
              )
            }
          >
            <Icon className="size-5" aria-hidden />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
