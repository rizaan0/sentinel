import type { ReactNode } from "react";
import { SfIcon, type SfSymbolName } from "./icons";

type Props = {
  children: ReactNode;
  tone?: "error" | "info" | "success";
};

const TONE = {
  error: "bg-[var(--color-danger-soft)] text-[var(--color-rose-700)] border-[var(--color-rose-100)]",
  info: "bg-[var(--color-ink-50)] text-[var(--color-ink-700)] border-[var(--color-border)]",
  success:
    "bg-[var(--color-accent-soft)] text-[var(--color-accent)] border-[var(--color-signal-200)]",
};

const SYMBOL: Record<NonNullable<Props["tone"]>, SfSymbolName> = {
  error: "exclamationmark.circle",
  info: "exclamationmark.circle",
  success: "checkmark",
};

export function InlineAlert({ children, tone = "error" }: Props) {
  return (
    <div
      role="alert"
      className={`flex items-start gap-2.5 rounded-[var(--radius-md)] border px-3 py-2.5 text-sm leading-snug ${TONE[tone]}`}
    >
      <SfIcon name={SYMBOL[tone]} weight="semibold" size={16} className="mt-0.5" />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
