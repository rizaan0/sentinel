type Props = {
  title: string;
  description?: string;
  action?: React.ReactNode;
};

export function EmptyState({ title, description, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-[var(--radius-xl)] border border-dashed border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] px-6 py-14 text-center">
      <p className="font-bold text-[var(--color-text)]">{title}</p>
      {description && (
        <p className="max-w-xs text-sm leading-relaxed text-[var(--color-text-muted)] text-pretty">
          {description}
        </p>
      )}
      {action && <div className="mt-1 w-full max-w-xs">{action}</div>}
    </div>
  );
}
