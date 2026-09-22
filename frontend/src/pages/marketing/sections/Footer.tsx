import { Link } from "react-router-dom";
import { LANDING_CHROME } from "../landingRail";

/**
 * Umbra-inspired footer: single quiet row — copyright leading, text links trailing.
 * No cards, no heavy borders; sits on the same chrome rail as the navbar.
 */
export default function Footer() {
  return (
    <footer className="relative z-10 shrink-0 pb-[max(1rem,env(safe-area-inset-bottom))]">
      <div
        className={`${LANDING_CHROME} flex flex-col gap-2 py-5 text-sm text-[var(--color-text-muted)] sm:flex-row sm:items-center sm:justify-between`}
      >
        <p>© {new Date().getFullYear()} Sentinel</p>
        <nav className="flex items-center gap-6" aria-label="Footer">
          <Link to="/login" className="transition-colors hover:text-[var(--color-text)]">
            Log in
          </Link>
          <Link to="/signup" className="transition-colors hover:text-[var(--color-text)]">
            Get Started
          </Link>
        </nav>
      </div>
    </footer>
  );
}
