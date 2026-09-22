import { formatAccountNumber } from "../../lib/formatAccountNumber";
import { CopyButton } from "./CopyButton";

type Props = {
  number: string;
  copyable?: boolean;
  className?: string;
};

/**
 * Formatted Sentinel account number with brand context and optional copy.
 * Copies the raw digits — display grouping is visual only.
 */
export function AccountNumber({ number, copyable = true, className = "" }: Props) {
  const display = formatAccountNumber(number);

  return (
    <span className={`inline-flex max-w-full items-center gap-2 ${className}`}>
      <span
        className="inline-flex min-w-0 items-baseline gap-1.5 font-mono text-sm font-medium text-[var(--color-text)]"
        title={number}
      >
        <span className="shrink-0 text-[0.7em] font-semibold uppercase tracking-[0.14em] text-[var(--color-text-muted)]">
          ST
        </span>
        <span className="select-none text-[var(--color-border-strong)]" aria-hidden>
          ·
        </span>
        <span className="tabular tracking-[0.12em]">{display}</span>
        <span className="sr-only">Account number {number}</span>
      </span>
      {copyable && <CopyButton value={number} label="Copy" />}
    </span>
  );
}
