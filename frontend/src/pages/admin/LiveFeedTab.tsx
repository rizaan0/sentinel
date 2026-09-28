import { ArrowLeftRight, ShieldAlert } from "lucide-react";
import type { LiveFeedEvent } from "../../lib/adminTypes";
import { formatAccountNumber } from "../../lib/formatAccountNumber";
import { humanizeLabel } from "../../lib/humanize";
import { BouncyAccordion } from "@/components/motion/bouncy-accordion";
import { EmptyState } from "../../components/ui/EmptyState";

function displayAccount(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.length === 12 && value.replace(/[\s-]/g, "") === digits) return formatAccountNumber(digits);
  return value;
}

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
 * One event opens at a time.
 */
export default function LiveFeedTab({
  events,
  connected,
}: {
  events: LiveFeedEvent[];
  connected: boolean;
}) {
  const items = events.map((event, index) => ({
    id: `${event.receivedAt}-${index}`,
    icon:
      event.type === "fraud_alert" ? (
        <ShieldAlert className="h-4 w-4" />
      ) : (
        <ArrowLeftRight className="h-4 w-4" />
      ),
    title: (
      <span className="flex min-w-0 items-center gap-3">
        <span
          className={`inline-flex shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
            event.type === "fraud_alert"
              ? "bg-[var(--color-danger-soft)] text-[var(--color-rose-700)]"
              : "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
          }`}
        >
          {event.type === "fraud_alert" ? "Fraud alert" : "Transaction"}
        </span>
        <span className="min-w-0 flex-1 truncate">{summarizePayload(event.type, event.payload)}</span>
        <span className="shrink-0 text-xs font-normal text-muted-foreground tabular">
          {new Date(event.receivedAt).toLocaleTimeString()}
        </span>
      </span>
    ),
    description: (
      <dl className="space-y-1 text-xs">
        {Object.entries(event.payload).map(([key, value]) => (
          <div key={key} className="grid grid-cols-[9rem_1fr] gap-3">
            <dt>{humanizeLabel(key)}</dt>
            <dd className="break-words text-foreground">{formatFeedValue(value)}</dd>
          </div>
        ))}
      </dl>
    ),
  }));

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

      {items.length > 0 && (
        <BouncyAccordion
          items={items}
          classNames={{
            title: "overflow-visible whitespace-normal",
          }}
        />
      )}
    </div>
  );
}
