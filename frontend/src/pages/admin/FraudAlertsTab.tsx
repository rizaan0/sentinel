import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { AlertStatus, FraudAlert } from "../../lib/adminTypes";
import AssistantPanel from "./AssistantPanel";
import { EmptyState } from "../../components/ui/EmptyState";
import { Modal } from "../../components/ui/Modal";
import { TransactionId } from "../../components/ui/TransactionId";

const STATUS_OPTIONS: AlertStatus[] = ["open", "investigating", "resolved", "false_positive"];

function riskTone(score: number): string {
  if (score >= 70) return "text-[var(--color-rose-600)]";
  if (score >= 40) return "text-[#b45309]";
  return "text-[var(--color-text-muted)]";
}

/**
 * Fraud alerts with investigation drawer for the AI assistant.
 */
export default function FraudAlertsTab() {
  const [alerts, setAlerts] = useState<FraudAlert[] | null>(null);
  const [active, setActive] = useState<FraudAlert | null>(null);

  const load = () => {
    api.get<FraudAlert[]>("/fraud-alerts").then((response) => setAlerts(response.data));
  };

  useEffect(load, []);

  const updateStatus = async (alertId: number, status: AlertStatus) => {
    await api.patch(`/fraud-alerts/${alertId}/status`, { status });
    load();
    setActive((prev) => (prev && prev.id === alertId ? { ...prev, status } : prev));
  };

  if (!alerts) {
    return <p className="text-sm text-[var(--color-text-muted)]">Loading alerts…</p>;
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Fraud alerts</h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Rule and ML signals with investigation status controls.
        </p>
      </div>

      {alerts.length === 0 && (
        <EmptyState
          title="No fraud alerts yet"
          description="Suspicious patterns from the monitoring engine will appear here."
        />
      )}

      <ul className="space-y-2">
        {alerts.map((alert) => (
          <li key={alert.id} className="surface-card p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-medium">
                  Account {alert.account_number}{" "}
                  <span className={`tabular ${riskTone(alert.risk_score)}`}>
                    · risk {alert.risk_score}
                  </span>
                </p>
                <p className="mt-1.5">
                  <TransactionId id={alert.transaction_public_id} copyable={false} />
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {alert.triggered_rules.slice(0, 3).map((rule) => (
                    <span
                      key={rule.rule_name}
                      className="rounded-full bg-[var(--color-ink-100)] px-2 py-0.5 text-[10px] font-medium text-[var(--color-ink-700)]"
                    >
                      {rule.rule_name}
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <label className="sr-only" htmlFor={`status-${alert.id}`}>
                  Alert status
                </label>
                <select
                  id={`status-${alert.id}`}
                  value={alert.status}
                  onChange={(e) => updateStatus(alert.id, e.target.value as AlertStatus)}
                  className="input !w-auto !py-2 text-sm"
                >
                  {STATUS_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option.replace("_", " ")}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => setActive(alert)}
                  className="btn-secondary !min-h-10 !px-3 !py-2 text-xs"
                >
                  Investigate
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>

      <Modal
        open={Boolean(active)}
        title={active ? `Investigate ${active.account_number}` : "Investigate"}
        onClose={() => setActive(null)}
      >
        {active && (
          <div className="space-y-4 max-h-[70vh] overflow-y-auto">
            <div className="flex flex-wrap items-center gap-2 text-sm text-[var(--color-text-muted)]">
              <span>
                Risk score{" "}
                <span className={`font-semibold tabular ${riskTone(active.risk_score)}`}>
                  {active.risk_score}
                </span>
              </span>
              <span aria-hidden>·</span>
              <TransactionId id={active.transaction_public_id} />
            </div>
            <ul className="space-y-2 text-sm">
              {active.triggered_rules.map((rule) => (
                <li key={rule.rule_name} className="rounded-[var(--radius-md)] bg-[var(--color-ink-50)] p-3">
                  <p className="font-semibold">{rule.rule_name}</p>
                  <p className="mt-1 text-[var(--color-text-muted)] text-pretty">{rule.explanation}</p>
                </li>
              ))}
            </ul>
            <AssistantPanel transactionId={active.transaction_public_id} />
          </div>
        )}
      </Modal>
    </div>
  );
}
