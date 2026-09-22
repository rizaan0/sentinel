import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { SlotText } from "slot-text/react";
import { api } from "../../lib/api";
import type { PaginatedTransactions } from "../../lib/types";
import { useAuth } from "../../lib/useAuth";
import { formatWhen, recentPeopleFromHistory } from "../../lib/recentPeople";
import { AccountNumber } from "../../components/ui/AccountNumber";
import { Amount } from "../../components/ui/Amount";
import { Avatar } from "../../components/ui/Avatar";
import { Button } from "../../components/ui/Button";
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
    <div className="space-y-8">
      <section className="surface-card shadow-[var(--shadow-md)]">
        <div className="flex flex-col gap-8 p-6">
          <div className="space-y-2">
            <p className="text-sm font-medium text-[var(--color-text-muted)]">Available balance</p>
            <div className="flex items-baseline gap-2.5">
              <SlotText
                text={user?.balance ?? "—"}
                className="text-[2.5rem] font-semibold leading-none tracking-tight tabular text-[var(--color-text)] sm:text-5xl"
                options={{ duration: 240, stagger: 24, bounce: 0.4 }}
              />
              <span className="text-base font-medium text-[var(--color-text-muted)]">ST</span>
            </div>
          </div>

          {user?.account_number && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-[var(--color-text-muted)]">Your account</p>
              <AccountNumber number={user.account_number} />
            </div>
          )}

          <Link to="/send" className="btn-primary w-full">
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
