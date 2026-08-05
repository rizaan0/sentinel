import { useEffect, useRef, useState } from "react";
import type { LiveFeedEvent } from "../../lib/adminTypes";
import { adminLiveFeedUrl } from "../../lib/ws";
import { useAuth } from "../../lib/useAuth";

const MAX_EVENTS = 50;

/**
 * Live transaction/fraud-alert feed: Redis Pub/Sub -> WebSocket Gateway ->
 * Admin Dashboard, driven directly off the Transaction Completed Event and
 * Monitoring Engine alerts (see backend app/services/realtime.py).
 */
export default function LiveFeedTab() {
  const { token } = useAuth();
  const [events, setEvents] = useState<LiveFeedEvent[]>([]);
  const [connected, setConnected] = useState(false);
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
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm">
        <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`} />
        {connected ? "Live" : "Disconnected"}
      </div>

      {events.length === 0 && (
        <p className="text-sm text-neutral-500">
          Waiting for live activity... perform a transfer to see it appear here instantly.
        </p>
      )}

      <ul className="space-y-2">
        {events.map((event, index) => (
          <li
            key={index}
            className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-3 text-sm"
          >
            <div className="flex items-center justify-between">
              <span
                className={
                  event.type === "fraud_alert"
                    ? "text-red-600 font-medium"
                    : "text-neutral-500 font-medium"
                }
              >
                {event.type === "fraud_alert" ? "Fraud alert" : "Transaction"}
              </span>
              <span className="text-xs text-neutral-400">
                {new Date(event.receivedAt).toLocaleTimeString()}
              </span>
            </div>
            <pre className="mt-1 text-xs overflow-x-auto whitespace-pre-wrap">
              {JSON.stringify(event.payload, null, 2)}
            </pre>
          </li>
        ))}
      </ul>
    </div>
  );
}
