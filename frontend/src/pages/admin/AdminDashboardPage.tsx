import { useState } from "react";
import { useAuth } from "../../lib/useAuth";
import OverviewTab from "./OverviewTab";
import LiveFeedTab from "./LiveFeedTab";
import FraudAlertsTab from "./FraudAlertsTab";
import ReconciliationTab from "./ReconciliationTab";
import PredictiveAnalyticsTab from "./PredictiveAnalyticsTab";

type Tab = "overview" | "live" | "alerts" | "reconciliation" | "predictions";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "live", label: "Live feed" },
  { id: "alerts", label: "Fraud alerts" },
  { id: "reconciliation", label: "Reconciliation" },
  { id: "predictions", label: "Predictive analytics" },
];

/**
 * Admin operational dashboard: a completely different environment from the
 * user payment app, focused on live monitoring and investigation
 * (per idea.md).
 */
export default function AdminDashboardPage() {
  const { logout, user } = useAuth();
  const [tab, setTab] = useState<Tab>("overview");

  return (
    <main className="min-h-screen p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Sentinel Admin</h1>
          <p className="text-sm text-neutral-500">{user?.full_name}</p>
        </div>
        <button onClick={logout} className="text-sm underline text-neutral-500">
          Log out
        </button>
      </div>

      <nav className="flex gap-2 border-b border-neutral-200 dark:border-neutral-800">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-2 text-sm border-b-2 -mb-px ${
              tab === t.id
                ? "border-neutral-900 dark:border-white font-medium"
                : "border-transparent text-neutral-500"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div>
        {tab === "overview" && <OverviewTab />}
        {tab === "live" && <LiveFeedTab />}
        {tab === "alerts" && <FraudAlertsTab />}
        {tab === "reconciliation" && <ReconciliationTab />}
        {tab === "predictions" && <PredictiveAnalyticsTab />}
      </div>
    </main>
  );
}
