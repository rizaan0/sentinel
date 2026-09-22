type Step = { id: string; label: string };

type Props = {
  steps: Step[];
  current: string;
};

export function Stepper({ steps, current }: Props) {
  const currentIndex = steps.findIndex((s) => s.id === current);

  return (
    <ol
      className="flex items-center gap-1 overflow-x-auto rounded-[var(--radius-pill)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-1.5"
      aria-label="Progress"
    >
      {steps.map((step, index) => {
        const done = index < currentIndex;
        const active = index === currentIndex;
        return (
          <li key={step.id} className="min-w-0 flex-1">
            <span
              className={`flex min-h-9 items-center justify-center gap-1.5 rounded-[var(--radius-pill)] px-2 text-xs font-semibold transition-colors ${
                active
                  ? "bg-[var(--color-surface-raised)] text-[var(--color-accent)] shadow-[var(--shadow-sm)]"
                  : done
                    ? "text-[var(--color-accent)]"
                    : "text-[var(--color-text-muted)]"
              }`}
              aria-current={active ? "step" : undefined}
            >
              <span className="tabular">{done ? "✓" : index + 1}</span>
              <span className="hidden truncate sm:inline">{step.label}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
