import { useEffect, useRef, useState } from "react";
import type { LiveFeedEvent } from "../../lib/adminTypes";
import { adminLiveFeedUrl } from "../../lib/ws";
import { useAuth } from "../../lib/useAuth";
import { EmptyState } from "../../components/ui/EmptyState";

const MAX_EVENTS = 50;

function summarizePayload(type: LiveFeedEvent["type"], payload: Record<string, unknown>): string {
  if (type === "fraud_alert") {
    const account = String(payload.account_number ?? payload.user_account_number ?? "—");
    const score = payload.risk_score ?? payload.score ?? "—";
    return `Account ${account} · risk ${score}`;
  }
  const amount = payload.amount ?? "—";
  const sender = String(payload.sender_name ?? payload.sender_account_number ?? "Sender");
  const receiver = String(payload.receiver_name ?? payload.receiver_account_number ?? "Receiver");
  return `${sender} → ${receiver} · ${amount} ST`;
}

/**
 * Live transaction/fraud-alert feed via WebSocket.
 */
export default function LiveFeedTab() {
  const { token } = useAuth();
  const [events, setEvents] = useState<LiveFeedEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!token) return;

    const socket = new WebSocket(adminLiveFeedUrl(token));
    socketRef.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as Omit<LiveFeedEvent, "receivedAt">;
        setEvents((prev) =>
          [{ ...parsed, receivedAt: new Date().toISOString() }, ...prev].slice(0, MAX_EVENTS),
        );
      } catch {
        // ignore malformed messages
      }
    };

    return () => socket.close();
  }, [token]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Live feed</h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Real-time transactions and fraud alerts.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-full bg-[var(--color-surface-raised)] px-3 py-1.5 text-xs font-medium border border-[var(--color-border)]">
          <span
            className={`h-2 w-2 rounded-full ${connected ? "bg-[var(--color-signal-500)]" : "bg-[var(--color-rose-500)]"}`}
          />
          {connected ? "Connected" : "Disconnected"}
        </div>
      </div>

      {events.length === 0 && (
        <EmptyState
          title="Waiting for live activity"
          description="Perform a transfer in the user app to see it appear here instantly."
          symbol="rectangle.stack"
        />
      )}

      <ul className="space-y-2">
        {events.map((event, index) => (
          <li key={`${event.receivedAt}-${index}`} className="surface-card overflow-hidden">
            <button
              type="button"
              onClick={() => setExpanded(expanded === index ? null : index)}
              className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left hover:bg-[var(--color-ink-50)]"
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
              <pre className="border-t border-[var(--color-border)] bg-[var(--color-ink-50)] px-4 py-3 text-xs overflow-x-auto whitespace-pre-wrap text-[var(--color-ink-700)]">
                {JSON.stringify(event.payload, null, 2)}
              </pre>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
