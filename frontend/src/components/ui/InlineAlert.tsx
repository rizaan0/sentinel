type Props = {
  children: React.ReactNode;
  tone?: "error" | "info" | "success";
};

const TONE = {
  error: "bg-[var(--color-danger-soft)] text-[var(--color-rose-700)] border-[var(--color-rose-100)]",
  info: "bg-[var(--color-ink-50)] text-[var(--color-ink-700)] border-[var(--color-border)]",
  success:
    "bg-[var(--color-accent-soft)] text-[var(--color-accent)] border-[var(--color-signal-200)]",
};

export function InlineAlert({ children, tone = "error" }: Props) {
  return (
    <div role="alert" className={`rounded-[var(--radius-md)] border px-3 py-2.5 text-sm ${TONE[tone]}`}>
      {children}
    </div>
  );
}
