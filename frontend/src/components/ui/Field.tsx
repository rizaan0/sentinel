import type { ReactNode } from "react";

type Props = {
  label: string;
  htmlFor: string;
  error?: string | null;
  hint?: string;
  children: ReactNode;
};

export function Field({ label, htmlFor, error, hint, children }: Props) {
  const errorId = error ? `${htmlFor}-error` : undefined;
  const hintId = hint ? `${htmlFor}-hint` : undefined;
  const describedBy = [errorId, hintId].filter(Boolean).join(" ") || undefined;

  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-sm font-medium text-[var(--color-text)]">
        {label}
      </label>
      <div className={describedBy ? undefined : undefined}>
        {/* Clone-ish: children should include aria-describedby via wrapping */}
        <div data-describedby={describedBy}>{children}</div>
      </div>
      {hint && !error && (
        <p id={hintId} className="text-xs text-[var(--color-text-muted)]">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className="text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}
    </div>
  );
}
