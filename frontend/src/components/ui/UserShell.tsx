import { useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../lib/useAuth";
import { BrandMark } from "./BrandMark";

const NAV = [
  { to: "/dashboard", label: "Home", icon: "⌂" },
  { to: "/send", label: "Send", icon: "↗" },
  { to: "/activity", label: "Activity", icon: "☰" },
  { to: "/profile", label: "Profile", icon: "◉" },
];

export function UserShell() {
  const { refreshUser } = useAuth();

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-lg flex-col bg-[var(--color-surface)]">
      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-[var(--color-border)] bg-white/95 px-4 py-3 backdrop-blur">
        <BrandMark size="sm" />
      </header>

      <main className="flex-1 px-4 pb-24 pt-5">
        <Outlet />
      </main>

      <nav
        className="fixed inset-x-0 bottom-0 z-20 border-t border-[var(--color-border)] bg-white/95 backdrop-blur"
        aria-label="Primary"
      >
        <ul className="mx-auto flex max-w-lg items-stretch justify-around px-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-1">
          {NAV.map((item) => (
            <li key={item.to} className="flex-1">
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  `flex min-h-14 flex-col items-center justify-center gap-0.5 rounded-[var(--radius-pill)] mx-1 text-xs font-semibold transition-colors duration-150 ${
                    isActive
                      ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                      : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
                  }`
                }
              >
                <span className="text-lg leading-none" aria-hidden>
                  {item.icon}
                </span>
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
