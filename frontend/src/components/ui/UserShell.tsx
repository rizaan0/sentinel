import { useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../lib/useAuth";
import { BrandMark } from "./BrandMark";
import { SfIconSwap, type SfSymbolName } from "./icons";

const NAV: { to: string; label: string; symbol: SfSymbolName }[] = [
  { to: "/dashboard", label: "Home", symbol: "house" },
  { to: "/activity", label: "Activity", symbol: "list.bullet" },
  { to: "/send", label: "Send", symbol: "paperplane" },
  { to: "/profile", label: "Profile", symbol: "person.crop.circle" },
];

/** Shared content + chrome width — one alignment edge for header, pages, and dock. */
export const APP_RAIL = "mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8";

export function UserShell() {
  const { refreshUser, user } = useAuth();

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  return (
    <div className="flex min-h-dvh w-full flex-col bg-[var(--color-surface)]">
      <header className="sticky top-0 z-20 border-b border-[var(--color-border)]/70 bg-[var(--color-surface)]/75 backdrop-blur-xl">
        <div className={`${APP_RAIL} flex h-12 items-center justify-between gap-4 sm:h-14`}>
          <BrandMark size="sm" />
          {user?.full_name && (
            <p className="max-w-[40%] truncate text-sm font-medium tracking-tight text-[var(--color-text-muted)]">
              {user.full_name}
            </p>
          )}
        </div>
      </header>

      <main className={`${APP_RAIL} flex w-full flex-1 flex-col py-5 pb-[7.5rem] sm:py-6 sm:pb-32`}>
        <Outlet />
      </main>

      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-30">
        <div
          className={`${APP_RAIL} flex justify-center pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-2`}
        >
          <nav
            className="liquid-glass pointer-events-auto w-full max-w-lg"
            aria-label="Primary"
          >
            <ul className="flex items-stretch gap-0.5 p-1.5">
              {NAV.map((item) => (
                <li key={item.to} className="min-w-0 flex-1">
                  <NavLink
                    to={item.to}
                    data-cuelume-toggle
                    className={({ isActive }) =>
                      `liquid-glass-item flex min-h-11 flex-col items-center justify-center gap-0.5 rounded-[1.15rem] px-1 text-[10px] font-semibold tracking-tight sm:min-h-12 sm:text-[11px] ${
                        isActive
                          ? "is-active text-[var(--color-accent)]"
                          : "text-[var(--color-text-muted)]"
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <SfIconSwap name={item.symbol} active={isActive} size={20} />
                        <span className="truncate">{item.label}</span>
                      </>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </div>
    </div>
  );
}
