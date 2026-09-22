import { Link } from "react-router-dom";

export function BrandMark({
  size = "md",
  inverse = false,
}: {
  size?: "sm" | "md" | "lg";
  inverse?: boolean;
}) {
  const text = size === "lg" ? "text-2xl" : size === "sm" ? "text-lg" : "text-xl";
  const mark = size === "lg" ? "h-9 w-9" : size === "sm" ? "h-7 w-7" : "h-8 w-8";

  return (
    <Link to="/" className="inline-flex items-center gap-2.5 no-underline">
      <span
        className={`inline-flex ${mark} items-center justify-center rounded-[10px] bg-[var(--color-accent)] text-white text-sm font-extrabold shadow-[0_4px_14px_var(--color-accent-glow)]`}
        aria-hidden
      >
        S
      </span>
      <span
        className={`font-extrabold tracking-tight lowercase ${text} ${
          inverse ? "text-white" : "text-[var(--color-text)]"
        }`}
      >
        sentinel
      </span>
    </Link>
  );
}
