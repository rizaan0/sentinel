import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { ReconciliationReport } from "../../lib/adminTypes";

/**
 * Reconciliation reports: identifies accounting mismatches independent of
 * the fraud/monitoring pipeline (per idea.md and the Architecture Rules).
 */
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
    try {
      await api.post("/reconciliation/run");
      load();
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-4">
      <button onClick={runNow} disabled={running} className="btn-primary">
        {running ? "Running..." : "Run reconciliation now"}
      </button>

      {!reports && <p className="text-sm text-neutral-500">Loading reports...</p>}
      {reports && reports.length === 0 && (
        <p className="text-sm text-neutral-500">No reconciliation reports yet.</p>
      )}

      <ul className="space-y-3">
        {reports?.map((report) => (
          <li
            key={report.id}
            className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-4"
          >
            <div className="flex items-center justify-between">
              <span
                className={
                  report.status === "clean" ? "text-green-600 font-medium" : "text-red-600 font-medium"
                }
              >
                {report.status}
              </span>
              <span className="text-xs text-neutral-400">
                {new Date(report.created_at).toLocaleString()} ({report.triggered_by})
              </span>
            </div>
            <p className="text-sm text-neutral-500 mt-1">
              {report.accounts_checked} accounts checked, {report.discrepancy_count} discrepancies
            </p>
            {report.discrepancies.length > 0 && (
              <ul className="mt-2 text-sm space-y-1">
                {report.discrepancies.map((d) => (
                  <li key={d.account_number} className="font-mono">
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
