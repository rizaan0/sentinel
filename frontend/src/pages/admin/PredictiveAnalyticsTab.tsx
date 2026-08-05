import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { RiskPrediction } from "../../lib/adminTypes";

const LEVEL_COLOR: Record<string, string> = {
  high: "text-red-600",
  medium: "text-amber-600",
  low: "text-neutral-500",
};

/**
 * Predictive Analytics: ranks users whose fraud-alert frequency/severity
 * is trending upward, estimating who is likely to become suspicious next
 * (per idea.md).
 */
export default function PredictiveAnalyticsTab() {
  const [predictions, setPredictions] = useState<RiskPrediction[] | null>(null);
  const [running, setRunning] = useState(false);

  const load = () => {
    api.get<RiskPrediction[]>("/predictions").then((response) => setPredictions(response.data));
  };

  useEffect(load, []);

  const runNow = async () => {
    setRunning(true);
    try {
      await api.post("/predictions/run");
      load();
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-4">
      <button onClick={runNow} disabled={running} className="btn-primary">
        {running ? "Running..." : "Run predictive analytics now"}
      </button>

      {!predictions && <p className="text-sm text-neutral-500">Loading predictions...</p>}
      {predictions && predictions.length === 0 && (
        <p className="text-sm text-neutral-500">
          No at-risk trends yet - predictions appear once users have recent fraud alerts.
        </p>
      )}

      <ul className="space-y-2">
        {predictions?.map((p) => (
          <li
            key={p.id}
            className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-4 flex items-center justify-between"
          >
            <div>
              <p className="font-mono font-medium">{p.account_number}</p>
              <p className="text-xs text-neutral-500">
                {p.alerts_last_7d} alerts this week (vs {p.alerts_prior_7d} the week before),
                avg risk {p.avg_risk_score_last_7d.toFixed(1)}
              </p>
            </div>
            <div className="text-right">
              <p className={`font-semibold ${LEVEL_COLOR[p.predicted_risk_level]}`}>
                {p.predicted_risk_level.toUpperCase()}
              </p>
              <p className="text-xs text-neutral-400">trend {p.trend_score.toFixed(1)}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
