import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { PlatformStats } from "../../lib/adminTypes";

export default function OverviewTab() {
  const [stats, setStats] = useState<PlatformStats | null>(null);

  useEffect(() => {
    api.get<PlatformStats>("/admin/stats").then((response) => setStats(response.data));
  }, []);

  if (!stats) {
    return <p className="text-sm text-neutral-500">Loading platform stats...</p>;
  }

  const cards: { label: string; value: string }[] = [
    { label: "Total users", value: String(stats.total_users) },
    { label: "Total transactions", value: String(stats.total_transactions) },
    { label: "Total volume", value: `${stats.total_volume} ST` },
    { label: "Open fraud alerts", value: String(stats.open_alerts) },
    {
      label: "Latest reconciliation",
      value: stats.latest_reconciliation_status ?? "never run",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-4"
        >
          <p className="text-xs text-neutral-500">{card.label}</p>
          <p className="text-xl font-semibold mt-1">{card.value}</p>
        </div>
      ))}
    </div>
  );
}
