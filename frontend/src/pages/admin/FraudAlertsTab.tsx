import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { humanizeLabel } from "../../lib/humanize";
import type { AlertStatus, FraudAlert, RuleStat } from "../../lib/adminTypes";
import AssistantPanel from "./AssistantPanel";
import { EmptyState } from "../../components/ui/EmptyState";
import { Modal } from "../../components/ui/Modal";
import { AccountNumber } from "../../components/ui/AccountNumber";
import { TransactionId } from "../../components/ui/TransactionId";
import { formatAccountNumber } from "../../lib/formatAccountNumber";

const STATUS_OPTIONS: AlertStatus[] = [
  "open",
  "investigating",
  "resolved",
  "false_positive",
  "confirmed_fraud",
];

function riskTone(score: number): string {
  if (score >= 70) return "text-[var(--color-rose-600)]";
  if (score >= 40) return "text-[#b45309]";
  return "text-[var(--color-text-muted)]";
}

/**
 * Fraud alerts with investigation drawer for the AI assistant.
 */
export default function FraudAlertsTab({ refreshKey = 0 }: { refreshKey?: number }) {
  const [alerts, setAlerts] = useState<FraudAlert[] | null>(null);
  const [stats, setStats] = useState<RuleStat[]>([]);
  const [active, setActive] = useState<FraudAlert | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reason, setReason] = useState("legitimate_group_payment");
  const [note, setNote] = useState("");
  const [caseView, setCaseView] = useState<{
    title: string;
    nodes: { id: string; type: string; label: string; role?: string }[];
    timeline: { at: string; kind: string; text: string }[];
  } | null>(null);
  const [feedback, setFeedback] = useState<{ matched: number; stayed_under_alert: number; later_confirmed: number } | null>(null);

  const load = () => {
    setLoadError(null);
    api
      .get<FraudAlert[]>("/fraud-alerts")
      .then((response) => setAlerts(response.data))
      .catch(() => setLoadError("Could not load fraud alerts."));
    api.get<{ matched: number; stayed_under_alert: number; later_confirmed: number }>("/fraud-alerts/pattern-feedback").then((response) => {
      setFeedback(response.data);
    }).catch(() => setFeedback(null));
    api.get<RuleStat[]>("/fraud-alerts/rule-stats").then((response) => {
      const rows = response.data;
      if (Array.isArray(rows) && rows.every((row) => row && "rule_id" in row)) {
        setStats(rows.filter((row) => row.alerts > 0));
      }
    });
  };

  useEffect(load, [refreshKey]);

  const openCase = (alert: FraudAlert) => {
    setActive(alert);
    api.get(`/fraud-alerts/${alert.id}/case`).then((response) => setCaseView(response.data)).catch(() => setCaseView(null));
  };

  const updateStatus = async (alertId: number, status: AlertStatus, reviewReason?: string) => {
    const response = await api.patch<FraudAlert>(`/fraud-alerts/${alertId}/status`, {
      status,
      reason: status === "false_positive" ? reviewReason || reason : undefined,
      note: status === "false_positive" ? note : undefined,
    });
    load();
    setActive((prev) => (prev && prev.id === alertId ? { ...prev, ...response.data } : prev));
  };

  const holdAction = async (alertId: number, action: "release" | "confirm") => {
    const response = await api.post<FraudAlert>(`/fraud-alerts/${alertId}/${action}`);
    load();
    setActive(response.data);
  };

  if (loadError) {
    return <p className="text-sm text-[var(--color-rose-600)]">{loadError}</p>;
  }

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
          symbol="exclamationmark.circle"
        />
      )}

      <ul className="space-y-2">
        {alerts.map((alert) => (
          <li key={alert.id} className="surface-card p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-medium">
                  <AccountNumber number={alert.account_number} copyable={false} />{" "}
                  <span className={`tabular ${riskTone(alert.risk_score)}`}>
                    · risk {alert.risk_score}
                  </span>
                  {alert.tier && (
                    <span className="ml-2 text-xs font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
                      {humanizeLabel(alert.tier)}
                    </span>
                  )}
                  {alert.pattern && (
                    <span className="ml-2 text-xs font-medium text-[var(--color-ink-700)]">
                      Pattern {alert.pattern}
                    </span>
                  )}
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
                      {humanizeLabel(rule.rule_name)}
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
                  onChange={(e) => {
                    const next = e.target.value as AlertStatus;
                    if (next === "false_positive") {
                      openCase(alert);
                      return;
                    }
                    void updateStatus(alert.id, next);
                  }}
                  className="input !w-auto min-h-11 py-2 text-sm"
                >
                  {STATUS_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {humanizeLabel(option)}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => openCase(alert)}
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
        title={active ? `Investigate ${formatAccountNumber(active.account_number)}` : "Investigate"}
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
            {active.outcome && (
              <p className="text-sm font-medium">{active.outcome}</p>
            )}
            {active.decision_trace?.action && (
              <p className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                Action {humanizeLabel(active.decision_trace.action)}
              </p>
            )}
            {active.narrative && (
              <p className="text-sm text-pretty text-[var(--color-text-muted)]">{active.narrative}</p>
            )}
            {active.decision_trace?.context && active.decision_trace.context.length > 0 && (
              <ul className="list-disc pl-5 text-sm">
                {active.decision_trace.context.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            )}
            <div className="space-y-1 text-sm">
              <p className="font-semibold">What would change this decision?</p>
              {(active.decision_trace?.counterfactuals ?? []).map((item) => (
                <p key={item.text}>{item.text}</p>
              ))}
              {active.decision_trace?.smallest_allow?.text && (
                <p>{active.decision_trace.smallest_allow.text}</p>
              )}
            </div>
            {active.context_checks?.some((check) => check.check === "reviewed_legitimate_pattern" && check.cleared) && (
              <p className="text-sm">This pattern was reviewed as legitimate.</p>
            )}
            {caseView && (
              <div className="space-y-2">
                <p className="text-sm font-semibold">{caseView.title}</p>
                <svg viewBox="0 0 360 120" className="w-full" role="img" aria-label="Case graph">
                  {caseView.nodes
                    .filter((node) => node.type === "account")
                    .map((node, index, list) => {
                      const x = 40 + (index * 280) / Math.max(list.length - 1, 1);
                      return (
                        <g key={node.id}>
                          <circle cx={x} cy={48} r={18} fill={node.role === "subject" ? "var(--color-accent)" : "var(--color-ink-200)"} />
                          <text x={x} y={90} textAnchor="middle" fontSize="10">
                            {node.label.split(" ")[0]}
                          </text>
                        </g>
                      );
                    })}
                </svg>
                <ol className="space-y-1 text-sm">
                  {caseView.timeline.map((item) => (
                    <li key={`${item.at}-${item.text}`}>
                      {new Date(item.at).toLocaleString()} · {item.text}
                    </li>
                  ))}
                </ol>
              </div>
            )}
            {feedback && (
              <p className="text-xs text-[var(--color-text-muted)]">
                Reviewed patterns matched {feedback.matched} evaluations. {feedback.stayed_under_alert} stayed under the alert line. {feedback.later_confirmed} were later confirmed fraud.
              </p>
            )}
            <ul className="space-y-2 text-sm">
              {(active.signals?.length
                ? active.signals.map((signal) => ({
                    key: signal.rule_id,
                    title: `${signal.rule_id} ${humanizeLabel(signal.rule_name)}`,
                    meta: `${signal.family} · ${signal.severity} · ${signal.score_contribution} pts`,
                    body: signal.explanation,
                  }))
                : active.triggered_rules.map((rule) => ({
                    key: rule.rule_name,
                    title: humanizeLabel(rule.rule_name),
                    meta: `${rule.risk_weight} pts`,
                    body: rule.explanation,
                  }))
              ).map((rule) => (
                <li key={rule.key} className="rounded-[var(--radius-md)] bg-[var(--color-ink-50)] p-3">
                  <p className="font-semibold">{rule.title}</p>
                  <p className="mt-0.5 text-xs text-[var(--color-text-muted)]">{rule.meta}</p>
                  <p className="mt-1 text-[var(--color-text-muted)] text-pretty">{rule.body}</p>
                </li>
              ))}
            </ul>
            {active.context_checks && active.context_checks.length > 0 && (
              <ul className="space-y-1 text-sm">
                {active.context_checks.map((check) => (
                  <li key={check.check}>
                    {humanizeLabel(check.check)}: {check.cleared ? "cleared" : "not cleared"}
                  </li>
                ))}
              </ul>
            )}
            {active.score_breakdown && (
              <p className="text-xs text-[var(--color-text-muted)]">
                Score {active.score_breakdown.final ?? active.risk_score}. Bonus{" "}
                {active.score_breakdown.combination_bonus ?? 0}. Reductions{" "}
                {active.score_breakdown.reductions ?? 0}.
              </p>
            )}
            <div className="space-y-2 rounded-[var(--radius-md)] border border-[var(--color-ink-200)] p-3 text-sm">
                {active.hold_amount && (
                <p>
                  Hold {active.hold_amount} ST · {active.hold_status ? humanizeLabel(active.hold_status) : ""}
                </p>
                )}
                {active.user_explanation && <p>User: {active.user_explanation}</p>}
                <div className="flex flex-wrap gap-2">
                  <button type="button" className="btn-secondary !min-h-10 !px-3 text-xs" onClick={() => holdAction(active.id, "release")}>
                    Release held transfer
                  </button>
                  <button type="button" className="btn-secondary !min-h-10 !px-3 text-xs" onClick={() => holdAction(active.id, "confirm")}>
                    Confirm fraud
                  </button>
                  <label className="sr-only" htmlFor="fp-reason">False positive reason</label>
                  <select id="fp-reason" className="input !w-auto min-h-10 text-xs" value={reason} onChange={(event) => setReason(event.target.value)}>
                    <option value="legitimate_group_payment">Legitimate group payment</option>
                    <option value="known_contacts">Known contacts</option>
                    <option value="salary_or_refund">Salary or refund</option>
                    <option value="other">Other</option>
                  </select>
                  <input className="input !w-auto min-h-10 text-xs" placeholder="Note (optional)" value={note} onChange={(event) => setNote(event.target.value)} />
                  <button type="button" className="btn-secondary !min-h-10 !px-3 text-xs" onClick={() => updateStatus(active.id, "false_positive", reason)}>
                    False positive
                  </button>
                  <button type="button" className="btn-secondary !min-h-10 !px-3 text-xs" onClick={() => api.post(`/fraud-alerts/${active.id}/restriction/lift`).then(() => openCase(active))}>
                    Lift restriction
                  </button>
                </div>
              </div>
            {stats.length > 0 && (
              <ul className="text-xs text-[var(--color-text-muted)]">
                {stats.map((stat) => (
                  <li key={stat.rule_id}>
                    {humanizeLabel(stat.rule_id)}: {stat.alerts} alerts, {stat.false_positives} false positives
                  </li>
                ))}
              </ul>
            )}
            <AssistantPanel transactionId={active.transaction_public_id} />
          </div>
        )}
      </Modal>
    </div>
  );
}
