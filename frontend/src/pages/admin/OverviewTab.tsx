import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { humanizeLabel } from "../../lib/humanize";
import type { PlatformStats } from "../../lib/adminTypes";

export default function OverviewTab({ refreshKey = 0 }: { refreshKey?: number }) {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    setLoadError(null);
    api
      .get<PlatformStats>("/admin/stats")
      .then((response) => setStats(response.data))
      .catch(() => setLoadError("Unable to load platform stats."));
  }, [refreshKey]);

  if (loadError) {
    return <p className="text-sm text-[var(--color-rose-600)]">{loadError}</p>;
  }

  if (!stats) {
    return <p className="text-sm text-[var(--color-text-muted)]">Loading platform stats…</p>;
  }

  const cards: { label: string; value: string; emphasize?: boolean }[] = [
    { label: "Total users", value: String(stats.total_users) },
    { label: "Total transactions", value: String(stats.total_transactions) },
    { label: "Total volume", value: `${stats.total_volume} ST` },
    {
      label: "Open fraud alerts",
      value: String(stats.open_alerts),
      emphasize: stats.open_alerts > 0,
    },
    {
      label: "Latest reconciliation",
      value: stats.latest_reconciliation_status
        ? humanizeLabel(stats.latest_reconciliation_status)
        : "Never run",
    },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Platform overview</h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Counts from the database. They update when a transfer or alert arrives.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
        {cards.map((card) => (
          <div key={card.label} className="surface-card p-4">
            <p className="text-xs font-medium text-[var(--color-text-muted)]">{card.label}</p>
            <p
              className={`mt-2 text-xl font-semibold tabular tracking-tight ${
                card.emphasize ? "text-[var(--color-rose-600)]" : "text-[var(--color-text)]"
              }`}
            >
              {card.value}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
