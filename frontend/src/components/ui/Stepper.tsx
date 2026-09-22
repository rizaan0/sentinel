import { SlotText } from "slot-text/react";
import { SfIcon } from "./icons";

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
              className={`flex min-h-9 items-center justify-center gap-1.5 rounded-[var(--radius-pill)] px-2 text-xs font-semibold tracking-tight transition-colors duration-150 ease-[cubic-bezier(0.2,0,0,1)] ${
                active
                  ? "bg-[var(--color-surface-raised)] text-[var(--color-accent)] shadow-[var(--shadow-sm)]"
                  : done
                    ? "text-[var(--color-accent)]"
                    : "text-[var(--color-text-muted)]"
              }`}
              aria-current={active ? "step" : undefined}
            >
              {done ? (
                <SfIcon name="checkmark" weight="semibold" size={14} />
              ) : (
                <SlotText
                  text={String(index + 1)}
                  className="tabular"
                  options={{ duration: 200, stagger: 20, bounce: 0.5 }}
                />
              )}
              <SlotText
                text={step.label}
                className="hidden truncate sm:inline"
                options={{ rollBy: "word", duration: 220, stagger: 30 }}
              />
            </span>
          </li>
        );
      })}
    </ol>
  );
}
