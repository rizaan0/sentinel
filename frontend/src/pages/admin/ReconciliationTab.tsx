import { useEffect, useState } from "react";
import { SlotText } from "slot-text/react";
import { api } from "../../lib/api";
import { cue } from "../../lib/cue";
import type { ReconciliationReport } from "../../lib/adminTypes";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";

export default function ReconciliationTab() {
  const [reports, setReports] = useState<ReconciliationReport[] | null>(null);
  const [running, setRunning] = useState(false);

  const load = () => {
    api
      .get<ReconciliationReport[]>("/reconciliation/reports")
      .then((response) => setReports(response.data));
  };

  useEffect(load, []);

  const runNow = async () => {
    setRunning(true);
    cue.loading();
    try {
      await api.post("/reconciliation/run");
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
          <h1 className="text-xl font-semibold tracking-tight">Reconciliation</h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Ledger vs wallet balance checks — independent of the fraud pipeline.
          </p>
        </div>
        <Button onClick={runNow} disabled={running}>
          <SlotText
            text={running ? "Running…" : "Run now"}
            options={{ rollBy: "word", duration: 200, stagger: 28 }}
          />
        </Button>
      </div>

      {!reports && <p className="text-sm text-[var(--color-text-muted)]">Loading reports…</p>}
      {reports && reports.length === 0 && (
        <EmptyState
          title="No reconciliation reports yet"
          description="Run reconciliation to compare wallet balances against ledger sums."
        />
      )}

      <ul className="space-y-2">
        {reports?.map((report) => (
          <li key={report.id} className="surface-card p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span
                className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${
                  report.status === "clean"
                    ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                    : "bg-[var(--color-danger-soft)] text-[var(--color-rose-700)]"
                }`}
              >
                <SlotText
                  text={report.status.replace("_", " ")}
                  options={{ rollBy: "word", duration: 200, stagger: 28 }}
                />
              </span>
              <span className="text-xs text-[var(--color-text-muted)]">
                {new Date(report.created_at).toLocaleString()} · {report.triggered_by}
              </span>
            </div>
            <p className="mt-2 text-sm text-[var(--color-text-muted)]">
              <span className="tabular font-medium text-[var(--color-text)]">
                {report.accounts_checked}
              </span>{" "}
              accounts checked ·{" "}
              <span className="tabular font-medium text-[var(--color-text)]">
                {report.discrepancy_count}
              </span>{" "}
              discrepancies
            </p>
            {report.discrepancies.length > 0 && (
              <ul className="mt-3 space-y-1 rounded-[var(--radius-md)] bg-[var(--color-ink-50)] p-3 font-mono text-xs">
                {report.discrepancies.map((d) => (
                  <li key={d.account_number}>
                    {d.account_number}: expected {d.expected_balance}, actual {d.actual_balance}{" "}
                    (diff {d.difference})
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
