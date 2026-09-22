import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import type { PaginatedTransactions, TransactionSummary } from "../../lib/types";
import { formatWhen } from "../../lib/recentPeople";
import { Amount } from "../../components/ui/Amount";
import { Avatar } from "../../components/ui/Avatar";
import { EmptyState } from "../../components/ui/EmptyState";
import { Button } from "../../components/ui/Button";

type Filter = "all" | "sent" | "received";

export default function ActivityPage() {
  const navigate = useNavigate();
  const [history, setHistory] = useState<PaginatedTransactions | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>("all");
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .get<PaginatedTransactions>("/transactions/history", { params: { limit: 20, offset: 0 } })
      .then((response) => {
        if (!cancelled) setHistory(response.data);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadMore = async () => {
    if (!history) return;
    setLoadingMore(true);
    try {
      const response = await api.get<PaginatedTransactions>("/transactions/history", {
        params: { limit: 20, offset: history.items.length },
      });
      setHistory({
        ...response.data,
        items: [...history.items, ...response.data.items],
      });
    } finally {
      setLoadingMore(false);
    }
  };

  const items = useMemo(() => {
    const list = history?.items ?? [];
    if (filter === "all") return list;
    return list.filter((tx) => tx.direction === filter);
  }, [history, filter]);

  const hasMore = (history?.items.length ?? 0) < (history?.total ?? 0);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Activity</h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Your complete ST Coin transfer history.
        </p>
      </div>

      <div className="flex gap-2" role="tablist" aria-label="Filter transactions">
        {(["all", "sent", "received"] as Filter[]).map((value) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={filter === value}
            onClick={() => setFilter(value)}
            className={`min-h-10 rounded-[var(--radius-pill)] px-4 text-sm font-semibold capitalize transition-colors ${
              filter === value
                ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                : "bg-[var(--color-surface-muted)] text-[var(--color-text-muted)]"
            }`}
          >
            {value}
          </button>
        ))}
      </div>

      {loading && <p className="text-sm text-[var(--color-text-muted)]">Loading…</p>}

      {!loading && items.length === 0 && (
        <EmptyState
          title="Nothing here yet"
          description="Transfers you send or receive will appear in this list."
          action={
            <Button onClick={() => navigate("/send")} fullWidth>
              Send money
            </Button>
          }
        />
      )}

      <ul className="surface-card divide-y divide-[var(--color-border)] overflow-hidden">
        {items.map((tx: TransactionSummary) => (
          <li key={tx.transaction_id}>
            <button
              type="button"
              onClick={() => navigate(`/activity/${tx.transaction_id}`)}
              className="flex w-full items-center gap-3 px-4 py-3.5 text-left hover:bg-[var(--color-ink-50)]"
            >
              <Avatar name={tx.counterparty_name} size="sm" />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{tx.counterparty_name}</p>
                <p className="text-xs text-[var(--color-text-muted)]">
                  {tx.direction === "sent" ? "Sent" : "Received"} · {formatWhen(tx.created_at)}
                </p>
                {tx.remark && (
                  <p className="truncate text-xs text-[var(--color-text-muted)]">{tx.remark}</p>
                )}
              </div>
              <Amount value={tx.amount} signed direction={tx.direction} size="sm" />
            </button>
          </li>
        ))}
      </ul>

      {hasMore && (
        <Button
          variant="secondary"
          fullWidth
          disabled={loadingMore}
          onClick={() => void loadMore()}
        >
          {loadingMore ? "Loading…" : "Load more"}
        </Button>
      )}
    </div>
  );
}
