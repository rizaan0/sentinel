import { useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../lib/useAuth";
import { BrandMark } from "./BrandMark";
import { SfIconSwap, type SfSymbolName } from "./icons";

const NAV: { to: string; label: string; symbol: SfSymbolName }[] = [
  { to: "/dashboard", label: "Home", symbol: "house" },
  { to: "/send", label: "Send", symbol: "paperplane" },
  { to: "/activity", label: "Activity", symbol: "list.bullet" },
  { to: "/profile", label: "Profile", symbol: "person.crop.circle" },
];

/** Shared content width for authenticated pages. */
export const APP_RAIL = "mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8";

export function UserShell() {
  const { refreshUser, user } = useAuth();

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  return (
    <div className="flex min-h-dvh w-full flex-col bg-[var(--color-surface)]">
      <header className="sticky top-0 z-20 border-b border-[var(--color-border)] bg-white/95 backdrop-blur">
        <div className={`${APP_RAIL} flex h-14 items-center justify-between gap-6 sm:h-16`}>
          <div className="flex min-w-0 items-center gap-8">
            <BrandMark size="sm" />
            <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
              {NAV.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  data-cuelume-toggle
                  className={({ isActive }) =>
                    `inline-flex items-center gap-2 rounded-[var(--radius-pill)] px-3.5 py-2 text-sm font-semibold tracking-tight transition-colors duration-150 ease-[cubic-bezier(0.2,0,0,1)] ${
                      isActive
                        ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                        : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <SfIconSwap name={item.symbol} active={isActive} size={18} />
                      {item.label}
                    </>
                  )}
                </NavLink>
              ))}
            </nav>
          </div>
          {user?.full_name && (
            <p className="hidden truncate text-sm tracking-tight text-[var(--color-text-muted)] lg:block">
              {user.full_name}
            </p>
          )}
        </div>
      </header>

      <main className={`${APP_RAIL} flex-1 py-6 pb-24 sm:py-8 md:pb-10`}>
        <Outlet />
      </main>

      <nav
        className="fixed inset-x-0 bottom-0 z-20 border-t border-[var(--color-border)] bg-white/95 backdrop-blur md:hidden"
        aria-label="Primary"
      >
        <ul className="flex items-stretch justify-around px-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-1">
          {NAV.map((item) => (
            <li key={item.to} className="flex-1">
              <NavLink
                to={item.to}
                data-cuelume-toggle
                className={({ isActive }) =>
                  `mx-1 flex min-h-14 flex-col items-center justify-center gap-0.5 rounded-[var(--radius-pill)] text-[11px] font-semibold tracking-tight transition-colors duration-150 ease-[cubic-bezier(0.2,0,0,1)] ${
                    isActive
                      ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                      : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <SfIconSwap name={item.symbol} active={isActive} size={22} />
                    {item.label}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
