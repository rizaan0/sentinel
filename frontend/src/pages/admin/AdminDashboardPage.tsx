import { useState } from "react";
import { useAuth } from "../../lib/useAuth";
import { cue } from "../../lib/cue";
import { BrandMark } from "../../components/ui/BrandMark";
import { Button } from "../../components/ui/Button";
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
  { id: "predictions", label: "Predictions" },
];

/**
 * Admin operational dashboard: monitoring chrome over the same five tabs.
 */
export default function AdminDashboardPage() {
  const { logout, user } = useAuth();
  const [tab, setTab] = useState<Tab>("overview");

  return (
    <div className="app-atmosphere min-h-dvh">
      <header className="border-b border-[var(--color-border)] bg-[var(--color-surface-raised)]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <BrandMark size="sm" />
            <span className="hidden rounded-[var(--radius-pill)] bg-[var(--color-accent-soft)] px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[var(--color-accent)] sm:inline">
              Ops
            </span>
          </div>
          <div className="flex items-center gap-3">
            <p className="hidden text-sm text-[var(--color-text-muted)] sm:block">{user?.full_name}</p>
            <Button
              variant="secondary"
              onClick={() => {
                cue.dismiss();
                logout();
              }}
              className="!min-h-10 !px-3 !py-2 text-xs"
            >
              Log out
            </Button>
          </div>
        </div>
        <nav
          className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-4 sm:px-6 lg:px-8"
          aria-label="Admin sections"
        >
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              data-cuelume-toggle
              onClick={() => setTab(t.id)}
              className={`min-h-11 shrink-0 border-b-2 px-3 text-sm font-medium transition-colors ${
                tab === t.id
                  ? "border-[var(--color-accent)] text-[var(--color-accent)]"
                  : "border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        {tab === "overview" && <OverviewTab />}
        {tab === "live" && <LiveFeedTab />}
        {tab === "alerts" && <FraudAlertsTab />}
        {tab === "reconciliation" && <ReconciliationTab />}
        {tab === "predictions" && <PredictiveAnalyticsTab />}
      </main>
    </div>
  );
}
