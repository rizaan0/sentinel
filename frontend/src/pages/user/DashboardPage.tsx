import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import type { PaginatedTransactions } from "../../lib/types";
import { useAuth } from "../../lib/useAuth";
import { formatWhen, recentPeopleFromHistory } from "../../lib/recentPeople";
import { Amount } from "../../components/ui/Amount";
import { Avatar } from "../../components/ui/Avatar";
import { Button } from "../../components/ui/Button";
import { CopyButton } from "../../components/ui/CopyButton";
import { EmptyState } from "../../components/ui/EmptyState";

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [history, setHistory] = useState<PaginatedTransactions | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    api
      .get<PaginatedTransactions>("/transactions/history", { params: { limit: 20 } })
      .then((response) => setHistory(response.data))
      .finally(() => setLoadingHistory(false));
  }, []);

  const recentPeople = useMemo(
    () => recentPeopleFromHistory(history?.items ?? [], 8),
    [history],
  );

  return (
    <div className="space-y-6">
      <section className="surface-card p-5 shadow-[var(--shadow-md)]">
        <p className="label-accent">Available balance</p>
        <p className="mt-2 text-4xl font-extrabold tracking-tight tabular text-[var(--color-text)]">
          {user?.balance}{" "}
          <span className="text-lg font-semibold text-[var(--color-text-muted)]">ST</span>
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <p className="font-mono text-xs text-[var(--color-text-muted)]">{user?.account_number}</p>
          {user?.account_number && <CopyButton value={user.account_number} label="Copy" />}
        </div>
        <div className="mt-5">
          <Link to="/send" className="btn-primary">
            Send money
          </Link>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-[var(--color-text-muted)]">Recent people</h2>
        {loadingHistory && <p className="text-sm text-[var(--color-text-muted)]">Loading…</p>}
        {!loadingHistory && recentPeople.length === 0 && (
          <EmptyState
            title="No recent recipients yet"
            description="Send money once and they’ll show up here for one-tap pay again."
            action={
              <Button onClick={() => navigate("/send")} fullWidth>
                Send your first transfer
              </Button>
            }
          />
        )}
        {recentPeople.length > 0 && (
          <ul className="flex gap-3 overflow-x-auto pb-1">
            {recentPeople.map((person) => (
              <li key={person.account_number}>
                <button
                  type="button"
                  onClick={() =>
                    navigate("/send", {
                      state: {
                        recipient: {
                          account_number: person.account_number,
                          full_name: person.full_name,
                        },
                      },
                    })
                  }
                  className="flex w-20 flex-col items-center gap-2 rounded-[var(--radius-lg)] p-2 transition-transform duration-150 ease-[cubic-bezier(0.2,0,0,1)] active:scale-[0.96] hover:bg-[var(--color-accent-soft)]"
                >
                  <Avatar name={person.full_name} />
                  <span className="w-full truncate text-center text-xs font-semibold">
                    {person.full_name.split(" ")[0]}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[var(--color-text-muted)]">Latest activity</h2>
          <Link
            to="/activity"
            className="text-xs font-semibold text-[var(--color-accent)] underline-offset-2 hover:underline"
          >
            See all
          </Link>
        </div>
        <ul className="surface-card divide-y divide-[var(--color-border)] overflow-hidden">
          {(history?.items ?? []).slice(0, 5).map((tx) => (
            <li key={tx.transaction_id}>
              <button
                type="button"
                onClick={() => navigate(`/activity/${tx.transaction_id}`)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-[var(--color-accent-soft)]"
              >
                <Avatar name={tx.counterparty_name} size="sm" />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold">{tx.counterparty_name}</p>
                  <p className="text-xs text-[var(--color-text-muted)]">{formatWhen(tx.created_at)}</p>
                </div>
                <Amount value={tx.amount} signed direction={tx.direction} size="sm" />
              </button>
            </li>
          ))}
          {!loadingHistory && (history?.items.length ?? 0) === 0 && (
            <li className="px-4 py-6 text-center text-sm text-[var(--color-text-muted)]">
              No transactions yet.
            </li>
          )}
        </ul>
      </section>
    </div>
  );
}
