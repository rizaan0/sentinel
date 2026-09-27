import { useEffect, useState } from "react";
import { SlotText } from "slot-text/react";
import { api } from "../../lib/api";
import { cue } from "../../lib/cue";
import { humanizeLabel } from "../../lib/humanize";
import type { ForecastPoint, RiskPrediction } from "../../lib/adminTypes";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";

const LEVEL_STYLE: Record<string, string> = {
  high: "text-[var(--color-rose-700)]",
  medium: "text-[#c2410c]",
  low: "text-[var(--color-text-muted)]",
};

function titleWord(value: string): string {
  const label = humanizeLabel(value);
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function arrow(trend: string): string {
  if (trend === "increasing") return "↑";
  if (trend === "decreasing") return "↓";
  return "→";
}

function dayLabel(offset: number): string {
  if (offset === 0) return "Today";
  if (offset > 0) return `+${offset}d`;
  return `${offset}d`;
}

function ForecastChart({ series }: { series: ForecastPoint[] }) {
  if (series.length < 2) return null;
  const width = 640;
  const height = 220;
  const pad = { left: 36, right: 16, top: 16, bottom: 32 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const xAt = (index: number) => pad.left + (index / (series.length - 1)) * innerW;
  const yAt = (score: number) => pad.top + (1 - score / 100) * innerH;
  const actual = series.filter((point) => point.kind === "actual");
  const predicted = series.filter((point) => point.kind === "predicted");
  const bridge = actual.length && predicted.length ? [actual[actual.length - 1], predicted[0]] : [];
  const path = (points: ForecastPoint[]) =>
    points
      .map((point, index) => {
        const at = series.indexOf(point);
        return `${index === 0 ? "M" : "L"} ${xAt(at).toFixed(1)} ${yAt(point.score).toFixed(1)}`;
      })
      .join(" ");
  const ticks = series.filter((point) => [-6, -3, 0, 3, 7].includes(point.offset));

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Seven day risk forecast">
      {[0, 20, 40, 60, 80, 100].map((mark) => (
        <g key={mark}>
          <line
            x1={pad.left}
            x2={width - pad.right}
            y1={yAt(mark)}
            y2={yAt(mark)}
            stroke="var(--color-border)"
          />
          <text x={0} y={yAt(mark) + 4} className="fill-[var(--color-text-muted)]" fontSize="11">
            {mark}
          </text>
        </g>
      ))}
      {actual.length > 1 && (
        <path d={path(actual)} fill="none" stroke="var(--color-ink-700)" strokeWidth="2.5" />
      )}
      {bridge.length === 2 && (
        <path d={path(bridge)} fill="none" stroke="var(--color-accent)" strokeWidth="2.5" />
      )}
      {predicted.length > 1 && (
        <path d={path(predicted)} fill="none" stroke="var(--color-accent)" strokeWidth="2.5" />
      )}
      {series.map((point) => (
        <circle
          key={`${point.kind}-${point.offset}`}
          cx={xAt(series.indexOf(point))}
          cy={yAt(point.score)}
          r="3.5"
          fill={point.kind === "actual" ? "var(--color-ink-700)" : "var(--color-accent)"}
        />
      ))}
      {ticks.map((point) => (
        <text
          key={point.offset}
          x={xAt(series.indexOf(point))}
          y={height - 8}
          textAnchor="middle"
          className="fill-[var(--color-text-muted)]"
          fontSize="11"
        >
          {dayLabel(point.offset)}
        </text>
      ))}
    </svg>
  );
}

export default function PredictiveAnalyticsTab() {
  const [predictions, setPredictions] = useState<RiskPrediction[] | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [running, setRunning] = useState(false);

  const load = () => {
    api.get<RiskPrediction[]>("/predictions").then((response) => {
      setPredictions(response.data);
      setSelectedId((current) => current ?? response.data[0]?.id ?? null);
    });
  };

  useEffect(load, []);

  const runNow = async () => {
    setRunning(true);
    cue.loading();
    try {
      const response = await api.post<RiskPrediction[]>("/predictions/run");
      setPredictions(response.data);
      setSelectedId(response.data[0]?.id ?? null);
      cue.success();
    } catch {
      cue.error();
    } finally {
      setRunning(false);
    }
  };

  const selected = predictions?.find((row) => row.id === selectedId) ?? predictions?.[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-2xl">
          <h1 className="text-xl font-semibold tracking-tight">Predictive analytics</h1>
          <p className="mt-1 text-sm text-pretty text-[var(--color-text-muted)]">
            Forecasting future account risk from recent behaviour. This is where risk is heading,
            not a fraud decision.
          </p>
        </div>
        <Button onClick={runNow} disabled={running}>
          <SlotText
            text={running ? "Running…" : "Run prediction"}
            options={{ rollBy: "word", duration: 200, stagger: 28 }}
          />
        </Button>
      </div>

      {!predictions && <p className="text-sm text-[var(--color-text-muted)]">Loading forecasts…</p>}
      {predictions && predictions.length === 0 && (
        <EmptyState
          title="No risk forecasts yet"
          description="Run a prediction after accounts have recent transfers or monitoring scores."
          symbol="exclamationmark.circle"
        />
      )}

      {predictions && predictions.length > 0 && selected && (
        <>
          <section className="surface-card overflow-x-auto p-4 sm:p-5">
            <h2 className="text-sm font-semibold">Accounts at rising risk</h2>
            <table className="mt-3 w-full min-w-[36rem] text-left text-sm">
              <thead className="text-xs text-[var(--color-text-muted)]">
                <tr>
                  <th className="py-2 font-medium">Account</th>
                  <th className="py-2 font-medium">Current risk</th>
                  <th className="py-2 font-medium">Predicted risk</th>
                  <th className="py-2 font-medium">Trend</th>
                </tr>
              </thead>
              <tbody>
                {predictions.map((row) => (
                  <tr
                    key={row.id}
                    onClick={() => setSelectedId(row.id)}
                    className={`cursor-pointer border-t border-[var(--color-border)] ${
                      row.id === selected.id ? "bg-[var(--color-ink-50)]" : ""
                    }`}
                  >
                    <td className="py-3 font-mono">{row.account_number}</td>
                    <td className="py-3 tabular">{row.current_risk}</td>
                    <td className="py-3 tabular">{row.predicted_7d_risk}</td>
                    <td className={`py-3 font-medium ${LEVEL_STYLE[row.predicted_risk_level]}`}>
                      {arrow(row.trend)} {titleWord(row.predicted_risk_level)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="surface-card p-4 sm:p-5">
            <h2 className="text-sm font-semibold">Risk forecast</h2>
            <p className="mt-1 font-mono text-sm">{selected.account_number}</p>
            <div className="mt-4">
              <ForecastChart series={selected.series} />
            </div>
            <p className="mt-2 flex flex-wrap gap-4 text-xs text-[var(--color-text-muted)]">
              <span>Actual</span>
              <span>Predicted</span>
            </p>
          </section>

          <section className="surface-card p-4 sm:p-5">
            <h2 className="text-sm font-semibold">
              {selected.risk_change > 0
                ? "Why the risk is expected to increase"
                : selected.risk_change < 0
                  ? "Why the risk is expected to decrease"
                  : "Why the risk is expected to hold"}
            </h2>
            <p className="mt-3 text-sm text-pretty">{selected.explanation}</p>
            {selected.drivers.length > 0 && (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-[var(--color-text-muted)]">
                {selected.drivers.map((driver) => (
                  <li key={driver}>{driver}</li>
                ))}
              </ul>
            )}
            <dl className="mt-4 grid gap-3 sm:grid-cols-2">
              <div>
                <dt className="text-xs text-[var(--color-text-muted)]">Current risk</dt>
                <dd className="tabular text-sm font-semibold">{selected.current_risk}/100</dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--color-text-muted)]">Predicted 7-day risk</dt>
                <dd className="tabular text-sm font-semibold">{selected.predicted_7d_risk}/100</dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--color-text-muted)]">Risk change</dt>
                <dd className="tabular text-sm font-semibold">
                  {selected.risk_change > 0 ? `+${selected.risk_change}` : selected.risk_change}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--color-text-muted)]">Trend</dt>
                <dd className="text-sm font-semibold">{titleWord(selected.trend)}</dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--color-text-muted)]">Forecast horizon</dt>
                <dd className="text-sm font-semibold">{selected.horizon_days} days</dd>
              </div>
            </dl>
          </section>
        </>
      )}
    </div>
  );
}
