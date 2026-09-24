import type { ReactNode } from "react";

type Props = {
  title: string;
  description?: string;
  /** Trailing controls (filters, actions) share the header row on sm+. */
  actions?: ReactNode;
};

/** Shared page title block — leading-aligned to the app rail. */
export function PageHeader({ title, description, actions }: Props) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between sm:gap-6">
      <div className="min-w-0 space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-balance text-[var(--color-text)]">
          {title}
        </h1>
        {description && (
          <p className="max-w-prose text-sm leading-relaxed text-[var(--color-text-muted)] text-pretty">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
