import { useEffect, useState } from "react";
import { SlotText } from "slot-text/react";
import { api } from "../../lib/api";
import { cue } from "../../lib/cue";
import type { RiskPrediction } from "../../lib/adminTypes";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";

const LEVEL_STYLE: Record<string, string> = {
  high: "bg-[var(--color-danger-soft)] text-[var(--color-rose-700)]",
  medium: "bg-[#fff7ed] text-[#c2410c]",
  low: "bg-[var(--color-ink-100)] text-[var(--color-ink-600)]",
};

export default function PredictiveAnalyticsTab() {
  const [predictions, setPredictions] = useState<RiskPrediction[] | null>(null);
  const [running, setRunning] = useState(false);

  const load = () => {
    api.get<RiskPrediction[]>("/predictions").then((response) => setPredictions(response.data));
  };

  useEffect(load, []);

  const runNow = async () => {
    setRunning(true);
    cue.loading();
    try {
      await api.post("/predictions/run");
      load();
      cue.success();
    } catch {
      cue.error();
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Predictive analytics</h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Accounts whose fraud-signal trends are rising.
          </p>
        </div>
        <Button onClick={runNow} disabled={running}>
          <SlotText
            text={running ? "Running…" : "Run now"}
            options={{ rollBy: "word", duration: 200, stagger: 28 }}
          />
        </Button>
      </div>

      {!predictions && (
        <p className="text-sm text-[var(--color-text-muted)]">Loading predictions…</p>
      )}
      {predictions && predictions.length === 0 && (
        <EmptyState
          title="No at-risk trends yet"
          description="Predictions appear once users have recent fraud alerts to trend on."
          symbol="exclamationmark.circle"
        />
      )}

      <ul className="space-y-2">
        {predictions?.map((p) => (
          <li key={p.id} className="surface-card flex items-center justify-between gap-4 p-4">
            <div>
              <p className="font-mono font-medium">{p.account_number}</p>
              <p className="mt-1 text-xs text-[var(--color-text-muted)]">
                <span className="tabular">{p.alerts_last_7d}</span> alerts this week (vs{" "}
                <span className="tabular">{p.alerts_prior_7d}</span> prior) · avg risk{" "}
                <span className="tabular">{p.avg_risk_score_last_7d.toFixed(1)}</span>
              </p>
            </div>
            <div className="text-right">
              <span
                className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase ${LEVEL_STYLE[p.predicted_risk_level]}`}
              >
                <SlotText
                  text={p.predicted_risk_level}
                  options={{ duration: 200, stagger: 24 }}
                />
              </span>
              <p className="mt-1 text-xs text-[var(--color-text-muted)] tabular">
                trend {p.trend_score.toFixed(1)}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
