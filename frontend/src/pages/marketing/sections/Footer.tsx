import { LANDING_FRAME, LANDING_PAD } from "../landingRail";

/**
 * Quiet footer row on the same chrome rail as the navbar.
 */
export default function Footer() {
  return (
    <footer className={`relative z-10 shrink-0 pb-[max(0.75rem,env(safe-area-inset-bottom))] ${LANDING_PAD}`}>
      <div
        className={`${LANDING_FRAME} flex flex-col gap-2 py-4 text-sm text-[var(--color-text-muted)] sm:flex-row sm:items-center sm:justify-between`}
      >
        <p>© {new Date().getFullYear()} Sentinel</p>
        <nav className="flex items-center gap-6" aria-label="Footer">
          <a href="#faq" className="transition-colors hover:text-[var(--color-text)]">
            FAQ
          </a>
          <a href="#terms" className="transition-colors hover:text-[var(--color-text)]">
            Terms
          </a>
        </nav>
      </div>
    </footer>
  );
}
