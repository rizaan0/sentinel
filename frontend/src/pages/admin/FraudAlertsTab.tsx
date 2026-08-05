import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { AlertStatus, FraudAlert } from "../../lib/adminTypes";
import AssistantPanel from "./AssistantPanel";

const STATUS_OPTIONS: AlertStatus[] = ["open", "investigating", "resolved", "false_positive"];

/**
 * Fraud alerts with risk scores, triggered-rule explanations, and
 * investigation status controls (per idea.md's admin dashboard spec).
 */
export default function FraudAlertsTab() {
  const [alerts, setAlerts] = useState<FraudAlert[] | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const load = () => {
    api.get<FraudAlert[]>("/fraud-alerts").then((response) => setAlerts(response.data));
  };

  useEffect(load, []);

  const updateStatus = async (alertId: number, status: AlertStatus) => {
    await api.patch(`/fraud-alerts/${alertId}/status`, { status });
    load();
  };

  if (!alerts) return <p className="text-sm text-neutral-500">Loading alerts...</p>;
  if (alerts.length === 0) return <p className="text-sm text-neutral-500">No fraud alerts yet.</p>;

  return (
    <ul className="space-y-3">
      {alerts.map((alert) => (
        <li
          key={alert.id}
          className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-4"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">
                Account {alert.account_number}{" "}
                <span className="text-red-600">risk {alert.risk_score}</span>
              </p>
              <p className="text-xs text-neutral-500 font-mono">
                {alert.transaction_public_id}
              </p>
            </div>
            <select
              value={alert.status}
              onChange={(e) => updateStatus(alert.id, e.target.value as AlertStatus)}
              className="input w-auto text-sm"
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => setExpandedId(expandedId === alert.id ? null : alert.id)}
            className="text-xs underline text-neutral-500 mt-2"
          >
            {expandedId === alert.id ? "Hide explanation" : "Show explanation"}
          </button>

          {expandedId === alert.id && (
            <>
              <ul className="mt-2 space-y-1 text-sm">
                {alert.triggered_rules.map((rule) => (
                  <li key={rule.rule_name}>
                    <span className="font-medium">{rule.rule_name}</span>: {rule.explanation}
                  </li>
                ))}
              </ul>
              <AssistantPanel transactionId={alert.transaction_public_id} />
            </>
          )}
        </li>
      ))}
    </ul>
  );
}
