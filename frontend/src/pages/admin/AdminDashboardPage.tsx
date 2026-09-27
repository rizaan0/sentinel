import { useEffect, useRef, useState } from "react";
import { useAuth } from "../../lib/useAuth";
import { cue } from "../../lib/cue";
import { api } from "../../lib/api";
import { adminLiveFeedUrl } from "../../lib/ws";
import { BrandMark } from "../../components/ui/BrandMark";
import { Button } from "../../components/ui/Button";
import type { LiveFeedEvent, PlatformTransaction, ScenarioInfo, ScenarioStatus } from "../../lib/adminTypes";
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

const MAX_EVENTS = 50;

function sameEvent(left: LiveFeedEvent, right: LiveFeedEvent): boolean {
  return left.type === right.type && left.payload.transaction_id === right.payload.transaction_id && left.payload.alert_id === right.payload.alert_id;
}

/**
 * Admin operational dashboard: monitoring chrome over the same five tabs.
 * One WebSocket stays open across tabs so transfers and alerts stay live.
 */
export default function AdminDashboardPage() {
  const { logout, user, token } = useAuth();
  const [tab, setTab] = useState<Tab>("overview");
  const [events, setEvents] = useState<LiveFeedEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const [scenarioId, setScenarioId] = useState("normal");
  const [scenarioOpen, setScenarioOpen] = useState(false);
  const scenarioMenuRef = useRef<HTMLDivElement>(null);
  const [scenario, setScenario] = useState<ScenarioStatus | null>(null);
  const [scenarioError, setScenarioError] = useState<string | null>(null);
  const [statsKey, setStatsKey] = useState(0);
  const [alertKey, setAlertKey] = useState(0);
  const [forecastKey, setForecastKey] = useState(0);
  const [reconcileKey, setReconcileKey] = useState(0);
  const scenarioRef = useRef<ScenarioStatus | null>(null);

  const pushEvent = (incoming: LiveFeedEvent) => {
    setEvents((prev) => {
      if (prev.some((item) => sameEvent(item, incoming))) return prev;
      return [incoming, ...prev].slice(0, MAX_EVENTS);
    });
    if (incoming.type === "transaction") setStatsKey((value) => value + 1);
    if (incoming.type === "fraud_alert") setAlertKey((value) => value + 1);
  };

  useEffect(() => {
    api.get<{ items: PlatformTransaction[] }>("/admin/transactions?limit=20").then((response) => {
      const history = response.data.items.map((item) => ({
        type: "transaction" as const,
        payload: { ...item },
        receivedAt: item.created_at,
      }));
      setEvents((prev) => {
        const fresh = prev.filter((item) => !history.some((old) => sameEvent(old, item)));
        return [...fresh, ...history].slice(0, MAX_EVENTS);
      });
    });
    api.get<ScenarioInfo[]>("/admin/scenarios").then((response) => {
      setScenarios(response.data);
      if (response.data[0]) setScenarioId(response.data[0].id);
    });
    api.get<ScenarioStatus>("/admin/scenarios/status").then((response) => {
      scenarioRef.current = response.data;
      setScenario(response.data);
    });
  }, []);

  useEffect(() => {
    if (!scenarioOpen) return;
    const close = (event: MouseEvent) => {
      if (!scenarioMenuRef.current?.contains(event.target as Node)) setScenarioOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setScenarioOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", onKey);
    };
  }, [scenarioOpen]);

  useEffect(() => {
    if (!token) return;
    const socket = new WebSocket(adminLiveFeedUrl(token));
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as Omit<LiveFeedEvent, "receivedAt">;
        pushEvent({ ...parsed, receivedAt: new Date().toISOString() });
      } catch {
        // ignore malformed messages
      }
    };
    return () => socket.close();
  }, [token]);

  useEffect(() => {
    if (scenario?.state !== "running") return;
    const timer = window.setInterval(() => {
      api.get<ScenarioStatus>("/admin/scenarios/status").then((response) => {
        const next = response.data;
        const previous = scenarioRef.current;
        scenarioRef.current = next;
        setScenario(next);
        const booksMoved =
          next.scenario_id === "reconciliation" && previous?.step !== next.step;
        if (booksMoved) setReconcileKey((value) => value + 1);
        if (previous?.state === "running" && next.state !== "running") {
          setForecastKey((value) => value + 1);
          setReconcileKey((value) => value + 1);
          setStatsKey((value) => value + 1);
        }
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [scenario?.state]);

  const startScenario = async () => {
    setScenarioError(null);
    try {
      const response = await api.post<ScenarioStatus>(`/admin/scenarios/${scenarioId}/start`);
      scenarioRef.current = response.data;
      setScenario(response.data);
    } catch {
      setScenarioError("Unable to start that scenario. Stop the one that is already running, then try again.");
    }
  };

  const stopScenario = async () => {
    setScenarioError(null);
    try {
      const response = await api.post<ScenarioStatus>("/admin/scenarios/stop");
      scenarioRef.current = response.data;
      setScenario(response.data);
    } catch {
      setScenarioError("Unable to stop the scenario.");
    }
  };

  const running = scenario?.state === "running";

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
              aria-current={tab === t.id ? "page" : undefined}
              className={`min-h-11 shrink-0 border-b-2 px-3 text-sm font-medium transition-[color,border-color] duration-150 ease-[cubic-bezier(0.2,0,0,1)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)] ${
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

      <div className="border-b border-[var(--color-border)] bg-[var(--color-surface)]">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-end sm:px-6 lg:px-8">
          <div className="relative min-w-0 flex-1 text-sm" ref={scenarioMenuRef}>
            <span id="scenario-label" className="mb-1 block text-xs font-medium text-[var(--color-text-muted)]">
              Scenario
            </span>
            <button
              type="button"
              aria-haspopup="listbox"
              aria-expanded={scenarioOpen}
              aria-labelledby="scenario-label"
              disabled={running || scenarios.length === 0}
              onClick={() => setScenarioOpen((open) => !open)}
              className="input flex min-h-11 items-center justify-between text-left disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span>{scenarios.find((item) => item.id === scenarioId)?.title ?? "Choose a scenario"}</span>
              <span aria-hidden className="text-[var(--color-text-muted)]">
                ▾
              </span>
            </button>
            {scenarioOpen && (
              <ul
                role="listbox"
                aria-labelledby="scenario-label"
                className="surface-card absolute z-20 mt-2 max-h-80 w-full overflow-auto p-1"
              >
                {scenarios.map((item) => {
                  const selected = item.id === scenarioId;
                  return (
                    <li key={item.id}>
                      <button
                        type="button"
                        role="option"
                        aria-selected={selected}
                        onClick={() => {
                          setScenarioId(item.id);
                          setScenarioOpen(false);
                        }}
                        className={`flex min-h-11 w-full items-center rounded-[var(--radius-md)] px-3 text-left text-sm transition-[background-color,color] duration-150 ease-[cubic-bezier(0.2,0,0,1)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--color-accent)] ${
                          selected
                            ? "bg-[var(--color-accent-soft)] font-medium text-[var(--color-accent)]"
                            : "text-[var(--color-text)] hover:bg-[var(--color-ink-50)]"
                        }`}
                      >
                        {item.title}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
          <div className="flex gap-2">
            <Button onClick={startScenario} disabled={running || scenarios.length === 0}>
              Start scenario
            </Button>
            <Button variant="secondary" onClick={stopScenario} disabled={!running}>
              Stop scenario
            </Button>
          </div>
          <p className="text-sm text-[var(--color-text-muted)] sm:max-w-sm" aria-live="polite">
            {scenarioError
              ? scenarioError
              : `${scenario?.title ? `${scenario.title}. ` : ""}${running ? `Step ${scenario?.step ?? 0} of ${scenario?.total ?? 0}. ` : ""}${scenario?.detail ?? "Idle"}`}
          </p>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        {tab === "overview" && <OverviewTab refreshKey={statsKey} />}
        {tab === "live" && <LiveFeedTab events={events} connected={connected} />}
        {tab === "alerts" && <FraudAlertsTab refreshKey={alertKey} />}
        {tab === "reconciliation" && <ReconciliationTab refreshKey={reconcileKey} />}
        {tab === "predictions" && <PredictiveAnalyticsTab refreshKey={forecastKey} />}
      </main>
    </div>
  );
}
