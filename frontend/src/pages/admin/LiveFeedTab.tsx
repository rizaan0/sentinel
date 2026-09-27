import { useState } from "react";
import type { LiveFeedEvent } from "../../lib/adminTypes";
import { formatAccountNumber } from "../../lib/formatAccountNumber";
import { humanizeLabel } from "../../lib/humanize";

function displayAccount(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.length === 12 && value.replace(/[\s-]/g, "") === digits) return formatAccountNumber(digits);
  return value;
}
import { EmptyState } from "../../components/ui/EmptyState";

function formatFeedValue(value: unknown): string {
  if (value == null || value === "") return "—";
  if (typeof value === "string") return displayAccount(humanizeLabel(value));
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map(formatFeedValue).join(", ");
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => `${humanizeLabel(key)}: ${formatFeedValue(item)}`)
      .join("; ");
  }
  return String(value);
}

function summarizePayload(type: LiveFeedEvent["type"], payload: Record<string, unknown>): string {
  if (type === "fraud_alert") {
    const account = String(payload.account_number ?? payload.user_account_number ?? "—");
    const score = payload.risk_score ?? payload.score ?? "—";
    return `Account ${displayAccount(account)} · risk ${score}`;
  }
  const amount = payload.amount ?? "—";
  const sender = displayAccount(String(payload.sender_name ?? payload.sender_account_number ?? "Sender"));
  const receiver = displayAccount(String(payload.receiver_name ?? payload.receiver_account_number ?? "Receiver"));
  return `${sender} → ${receiver} · ${amount} ST`;
}

/**
 * Live transaction/fraud-alert feed via WebSocket.
 */
export default function LiveFeedTab({
  events,
  connected,
}: {
  events: LiveFeedEvent[];
  connected: boolean;
}) {
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Live feed</h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Real-time transactions and fraud alerts.
          </p>
        </div>
        <div
          className="flex min-h-11 items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-3 py-1.5 text-xs font-medium"
          role="status"
        >
          <span
            className={`h-2 w-2 rounded-full ${connected ? "bg-[var(--color-signal-500)]" : "bg-[var(--color-rose-500)]"}`}
          />
          {connected ? "Connected" : "Disconnected"}
        </div>
      </div>

      {events.length === 0 && (
        <EmptyState
          title="Waiting for live activity"
          description="Start a scenario, or send money in the user app. New transfers and alerts appear here."
          symbol="rectangle.stack"
        />
      )}

      <ul className="space-y-2">
        {events.map((event, index) => (
          <li key={`${event.receivedAt}-${index}`} className="surface-card overflow-hidden">
            <button
              type="button"
              aria-expanded={expanded === index}
              onClick={() => setExpanded(expanded === index ? null : index)}
              className="flex min-h-11 w-full items-start justify-between gap-3 px-4 py-3 text-left transition-[background-color] duration-150 ease-[cubic-bezier(0.2,0,0,1)] hover:bg-[var(--color-ink-50)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--color-accent)]"
            >
              <div>
                <span
                  className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                    event.type === "fraud_alert"
                      ? "bg-[var(--color-danger-soft)] text-[var(--color-rose-700)]"
                      : "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                  }`}
                >
                  {event.type === "fraud_alert" ? "Fraud alert" : "Transaction"}
                </span>
                <p className="mt-1.5 text-sm font-medium">
                  {summarizePayload(event.type, event.payload)}
                </p>
              </div>
              <span className="shrink-0 text-xs text-[var(--color-text-muted)] tabular">
                {new Date(event.receivedAt).toLocaleTimeString()}
              </span>
            </button>
            {expanded === index && (
              <dl className="space-y-1 border-t border-[var(--color-border)] bg-[var(--color-ink-50)] px-4 py-3 text-xs text-[var(--color-ink-700)]">
                {Object.entries(event.payload).map(([key, value]) => (
                  <div key={key} className="grid grid-cols-[9rem_1fr] gap-3">
                    <dt className="text-[var(--color-text-muted)]">{humanizeLabel(key)}</dt>
                    <dd className="break-words">{formatFeedValue(value)}</dd>
                  </div>
                ))}
              </dl>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
