import { Link } from "react-router-dom";
import { BrandMark } from "../../../components/ui/BrandMark";
import { SfIcon } from "../../../components/ui/icons";
import { LANDING_CHROME } from "../landingRail";

export default function Navbar() {
  return (
    <header className="relative z-50 shrink-0 border-b border-[var(--color-border)]/60 bg-white/80 backdrop-blur-md">
      <nav className={`${LANDING_CHROME} flex h-14 items-center justify-between`}>
        <BrandMark size="sm" />
        <div className="flex items-center gap-2 sm:gap-3">
          <Link
            to="/login"
            className="inline-flex min-h-10 items-center px-3 text-sm font-medium tracking-tight text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text)]"
          >
            Log in
          </Link>
          <Link to="/signup" className="btn-primary !min-h-10 !px-4 !py-2 text-sm">
            Get Started
            <SfIcon name="arrow.right" weight="semibold" size={14} />
          </Link>
        </div>
      </nav>
    </header>
  );
}
