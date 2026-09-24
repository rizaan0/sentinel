import type { ReactNode } from "react";
import { SfIcon, type SfSymbolName } from "./icons";

type Props = {
  title: string;
  description?: string;
  action?: ReactNode;
  /** SF Symbol shown above the title. */
  symbol?: SfSymbolName;
};

export function EmptyState({
  title,
  description,
  action,
  symbol = "tray",
}: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-[var(--radius-xl)] border border-dashed border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] px-6 py-10 text-center sm:py-12">
      <span className="flex size-12 items-center justify-center rounded-full bg-[var(--color-surface-raised)] text-[var(--color-text-muted)] shadow-[var(--shadow-sm)]">
        <SfIcon name={symbol} weight="regular" size={24} />
      </span>
      <p className="font-semibold tracking-tight text-[var(--color-text)]">{title}</p>
      {description && (
        <p className="max-w-xs text-sm leading-relaxed text-[var(--color-text-muted)] text-pretty">
          {description}
        </p>
      )}
      {action && <div className="mt-1 w-full max-w-xs">{action}</div>}
    </div>
  );
}
