import { useEffect, useState } from "react";
import { SlotText } from "slot-text/react";
import { api } from "../../lib/api";
import { cue } from "../../lib/cue";
import type { ReconciliationDiscrepancy, ReconciliationReport } from "../../lib/adminTypes";
import { AccountNumber } from "../../components/ui/AccountNumber";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";

function mismatchKey(report: ReconciliationReport): string {
  return report.discrepancies
    .map((row) => `${row.account_number}:${row.difference}`)
    .sort()
    .join("|");
}

function money(value: string): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return value;
  return amount.toFixed(2);
}

function meaning(difference: string): string {
  const value = Number(difference);
  const amount = money(String(Math.abs(value)));
  if (!Number.isFinite(value) || value === 0) {
    return "The wallet and the ledger match.";
  }
  if (value > 0) {
    return `The wallet is ${amount} ST higher than the ledger. The balance includes money the ledger does not record.`;
  }
  return `The wallet is ${amount} ST lower than the ledger. The ledger records money that is not in the wallet.`;
}

function groupRuns(reports: ReconciliationReport[]): ReconciliationReport[][] {
  const groups: ReconciliationReport[][] = [];
  for (const report of reports) {
    const key = mismatchKey(report);
    const current = groups.find((group) => mismatchKey(group[0]) === key);
    if (current) current.push(report);
    else groups.push([report]);
  }
  return groups;
}

function DiscrepancyRow({ row }: { row: ReconciliationDiscrepancy }) {
  const value = Number(row.difference);
  const signed = Number.isFinite(value) && value > 0 ? `+${money(row.difference)}` : money(row.difference);
  return (
    <li className="border-t border-[var(--color-border)] py-4 first:border-t-0 first:pt-0">
      <AccountNumber number={row.account_number} />
      <dl className="mt-3 grid gap-3 sm:grid-cols-3">
        <div>
          <dt className="text-xs font-medium text-[var(--color-text-muted)]">Expected · ledger</dt>
          <dd className="mt-1 tabular text-sm font-semibold">{money(row.expected_balance)} ST</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-[var(--color-text-muted)]">Actual · wallet</dt>
          <dd className="mt-1 tabular text-sm font-semibold">{money(row.actual_balance)} ST</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-[var(--color-text-muted)]">Difference</dt>
          <dd className="mt-1 tabular text-sm font-semibold text-[var(--color-rose-700)]">{signed} ST</dd>
        </div>
      </dl>
      <p className="mt-3 text-sm text-pretty text-[var(--color-text-muted)]">{meaning(row.difference)}</p>
    </li>
  );
}

export default function ReconciliationTab({ refreshKey = 0 }: { refreshKey?: number }) {
  const [reports, setReports] = useState<ReconciliationReport[] | null>(null);
  const [running, setRunning] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = () => {
    setLoadError(null);
    api
      .get<ReconciliationReport[]>("/reconciliation/reports")
      .then((response) => setReports(response.data))
      .catch(() => setLoadError("Unable to load reconciliation checks."));
  };

  useEffect(load, [refreshKey]);

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

  const latest = reports?.[0];
  const earlier = reports?.slice(1) ?? [];
  const latestKey = latest ? mismatchKey(latest) : "";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-2xl">
          <h1 className="text-xl font-semibold tracking-tight">Reconciliation</h1>
          <p className="mt-1 text-sm text-pretty text-[var(--color-text-muted)]">
            Each check compares one number from the ledger with one number from the wallet. The
            ledger sum is what the account should hold. The wallet balance is what Sentinel shows.
            They must match. This check does not score fraud.
          </p>
        </div>
        <Button onClick={runNow} disabled={running}>
          <SlotText
            text={running ? "Running…" : "Run check"}
            options={{ rollBy: "word", duration: 200, stagger: 28 }}
          />
        </Button>
      </div>

      {loadError && <p className="text-sm text-[var(--color-rose-600)]">{loadError}</p>}
      {!loadError && !reports && <p className="text-sm text-[var(--color-text-muted)]">Loading the latest check…</p>}
      {reports && !latest && (
        <EmptyState
          title="No reconciliation check yet"
          description="Run a check to compare each wallet with its ledger sum."
          symbol="rectangle.stack"
        />
      )}

      {latest && (
        <section className="surface-card p-4 sm:p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold">Current check</h2>
              <p className="mt-1 text-sm text-[var(--color-text-muted)]">
                {new Date(latest.created_at).toLocaleString()} · {latest.triggered_by} ·{" "}
                {latest.accounts_checked} accounts
              </p>
            </div>
            <span
              className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                latest.status === "clean"
                  ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                  : "bg-[var(--color-danger-soft)] text-[var(--color-rose-700)]"
              }`}
            >
              {latest.status === "clean" ? "Books match" : `${latest.discrepancy_count} out of balance`}
            </span>
          </div>

          {latest.discrepancies.length === 0 ? (
            <p className="mt-4 text-sm text-pretty">
              Every wallet balance matches its ledger sum. Nothing needs investigation from this check.
            </p>
          ) : (
            <ul className="mt-4">
              {latest.discrepancies.map((row) => (
                <DiscrepancyRow key={row.account_number} row={row} />
              ))}
            </ul>
          )}
        </section>
      )}

      {earlier.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold">Earlier checks</h2>
          <p className="text-sm text-[var(--color-text-muted)]">
            Scheduled runs save a report each time. Identical results are grouped, so the same accounts
            are not listed again.
          </p>
          <ul className="space-y-2">
            {groupRuns(earlier).map((group) => {
              const newest = group[0];
              const oldest = group[group.length - 1];
              const repeated = mismatchKey(newest) === latestKey;
              return (
                <li key={newest.id} className="surface-card px-4 py-3 text-sm">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <p className="font-medium">
                      {newest.status === "clean"
                        ? "Books matched"
                        : `${newest.discrepancy_count} out of balance`}
                      {group.length > 1 ? ` · ${group.length} runs` : ""}
                    </p>
                    <p className="text-xs text-[var(--color-text-muted)]">
                      {group.length > 1
                        ? `${new Date(oldest.created_at).toLocaleString()} – ${new Date(newest.created_at).toLocaleString()}`
                        : `${new Date(newest.created_at).toLocaleString()} · ${newest.triggered_by}`}
                    </p>
                  </div>
                  <p className="mt-1 text-[var(--color-text-muted)]">
                    {newest.accounts_checked} accounts checked.
                    {newest.discrepancy_count > 0 &&
                      (repeated
                        ? " Same accounts as the current check."
                        : " Different from the current check.")}
                  </p>
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </div>
  );
}
