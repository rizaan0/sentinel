import { Link } from "react-router-dom";
import { BrandMark } from "../../../components/ui/BrandMark";

export default function Navbar() {
  return (
    <header className="relative z-50 shrink-0 border-b border-[var(--color-border)] bg-white/90 backdrop-blur">
      <nav className="mx-auto flex h-14 max-w-5xl items-center justify-between px-5 sm:px-6">
        <BrandMark size="sm" />
        <div className="flex items-center gap-2">
          <Link to="/login" className="btn-ghost !min-h-10 text-sm font-semibold">
            Log in
          </Link>
          <Link to="/signup" className="btn-primary !min-h-10 !px-4 !py-2 text-sm">
            Get Started
          </Link>
        </div>
      </nav>
    </header>
  );
}
