import { Link } from "react-router-dom";

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 backdrop-blur bg-white/70 dark:bg-neutral-950/70 border-b border-neutral-200 dark:border-neutral-800">
      <nav className="max-w-6xl mx-auto flex items-center justify-between px-6 py-4">
        <span className="font-semibold text-lg tracking-tight">Sentinel</span>
        <div className="flex items-center gap-4">
          <Link
            to="/login"
            className="text-sm text-neutral-600 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-white"
          >
            Log in
          </Link>
          <Link to="/signup" className="btn-primary text-sm">
            Sign up
          </Link>
        </div>
      </nav>
    </header>
  );
}
