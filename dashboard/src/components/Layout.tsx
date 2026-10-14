import { Activity, BarChart3, Ban, Inbox, LogOut, MapPinned, Rocket, Users } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useLogout, useMe } from "@/lib/auth";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Overview", icon: Activity, mobile: true },
  { to: "/campaigns", label: "Campaigns", icon: Rocket, mobile: true },
  { to: "/leads", label: "Leads", icon: Users, mobile: true },
  { to: "/approvals", label: "Approvals", icon: Inbox, mobile: true },
  { to: "/analytics", label: "Analytics", icon: BarChart3, mobile: true },
  { to: "/targets", label: "Targets", icon: MapPinned, mobile: false },
  { to: "/suppression", label: "Do not contact", icon: Ban, mobile: false },
];

export function Layout() {
  const me = useMe();
  const logout = useLogout();
  return (
    <div className="min-h-dvh pb-20 md:pb-0">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4">
          <span className="font-semibold tracking-tight">LeadForge</span>
          <nav className="hidden gap-1 overflow-x-auto md:flex" aria-label="Main">
            {NAV.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  cn(
                    "rounded-md px-3 py-2 text-sm whitespace-nowrap",
                    isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100",
                  )
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2 text-sm text-slate-600">
            {NAV.filter((n) => !n.mobile).map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                aria-label={label}
                className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-md hover:bg-slate-100 md:hidden"
              >
                <Icon className="size-4" aria-hidden />
              </NavLink>
            ))}
            <span className="hidden lg:inline">{me.data?.email}</span>
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
        className="fixed inset-x-0 bottom-0 grid grid-cols-5 border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)] md:hidden"
      >
        {NAV.filter((n) => n.mobile).map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
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
