import { formatTransactionRef } from "../../lib/formatTransactionId";
import { CopyButton } from "./CopyButton";

type Props = {
  id: string;
  /** Show inline copy control (copies the full id). */
  copyable?: boolean;
  className?: string;
};

/**
 * Soft reference for UUID transaction ids — short mono label,
 * full value via title + screen reader text, and optional copy.
 */
export function TransactionId({ id, copyable = true, className = "" }: Props) {
  const short = formatTransactionRef(id);

  return (
    <span className={`inline-flex max-w-full items-center gap-2 ${className}`}>
      <span
        className="inline-flex items-baseline gap-1.5 font-mono text-sm font-medium tracking-wide text-[var(--color-text)]"
        title={id}
      >
        <span className="text-[0.7em] font-semibold uppercase tracking-[0.14em] text-[var(--color-text-muted)]">
          ST
        </span>
        <span className="select-none text-[var(--color-border-strong)]" aria-hidden>
          ·
        </span>
        <span className="tabular tracking-[0.08em]">{short}</span>
        <span className="sr-only">Full transaction ID: {id}</span>
      </span>
      {copyable && <CopyButton value={id} label="Copy" />}
    </span>
  );
}
