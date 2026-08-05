import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import type { PaginatedTransactions } from "../../lib/types";
import { useAuth } from "../../lib/useAuth";

/**
 * User dashboard: balance, recent transactions, and entry point into the
 * Send Money wizard (per idea.md's GPay/PhonePe-inspired design).
 */
export default function DashboardPage() {
  const { user, logout } = useAuth();
  const [history, setHistory] = useState<PaginatedTransactions | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    api
      .get<PaginatedTransactions>("/transactions/history", { params: { limit: 10 } })
      .then((response) => setHistory(response.data))
      .finally(() => setLoadingHistory(false));
  }, []);

  return (
    <main className="min-h-screen p-6 max-w-lg mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <button onClick={logout} className="text-sm underline text-neutral-500">
          Log out
        </button>
      </div>

      <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-4 space-y-1">
        <p className="text-sm text-neutral-500">Balance</p>
        <p className="text-3xl font-semibold">{user?.balance} ST</p>
        <p className="text-xs text-neutral-500 font-mono">
          Account number: {user?.account_number}
        </p>
      </div>

      <Link to="/send" className="btn-primary block text-center">
        Send money
      </Link>

      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-neutral-500">Recent transactions</h2>
        {loadingHistory && <p className="text-sm text-neutral-500">Loading...</p>}
        {!loadingHistory && history?.items.length === 0 && (
          <p className="text-sm text-neutral-500">No transactions yet.</p>
        )}
        <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
          {history?.items.map((tx) => (
            <li key={tx.transaction_id} className="py-3 flex items-center justify-between">
              <div>
                <p className="font-medium">{tx.counterparty_name}</p>
                <p className="text-xs text-neutral-500 font-mono">
                  {tx.counterparty_account_number}
                </p>
                {tx.remark && <p className="text-xs text-neutral-500">{tx.remark}</p>}
              </div>
              <p
                className={
                  tx.direction === "sent"
                    ? "text-red-600 font-medium"
                    : "text-green-600 font-medium"
                }
              >
                {tx.direction === "sent" ? "-" : "+"}
                {tx.amount} ST
              </p>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
