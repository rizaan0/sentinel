import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { SlotText } from "slot-text/react";
import { api } from "../../lib/api";
import type { AmountHoldNotice, PaginatedTransactions } from "../../lib/types";
import { useAuth } from "../../lib/useAuth";
import { formatWhen, recentPeopleFromHistory } from "../../lib/recentPeople";
import { AccountNumber } from "../../components/ui/AccountNumber";
import { Amount } from "../../components/ui/Amount";
import { Avatar } from "../../components/ui/Avatar";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { PageHeader } from "../../components/ui/PageHeader";
import { SfIcon } from "../../components/ui/icons";

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [history, setHistory] = useState<PaginatedTransactions | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [holds, setHolds] = useState<AmountHoldNotice[]>([]);
  const [restricted, setRestricted] = useState(false);
  const [heldTransfers, setHeldTransfers] = useState<{ transaction_id: string; amount: string }[]>([]);
  const [explanation, setExplanation] = useState("");

  useEffect(() => {
    api
      .get<PaginatedTransactions>("/transactions/history", { params: { limit: 20 } })
      .then((response) => setHistory(response.data))
      .finally(() => setLoadingHistory(false));
    api
      .get<AmountHoldNotice[]>("/holds/me")
      .then((response) => setHolds(response.data))
      .catch(() => setHolds([]));
    api
      .get<{ restricted: boolean; held: { transaction_id: string; amount: string }[] }>("/holds/flags")
      .then((response) => {
        setRestricted(response.data.restricted);
        setHeldTransfers(response.data.held);
      })
      .catch(() => {
        setRestricted(false);
        setHeldTransfers([]);
      });
  }, []);

  const submitExplanation = async (holdId: number) => {
    const text = explanation.trim();
    if (!text) return;
    await api.post(`/holds/${holdId}/explanation`, { text });
    setExplanation("");
    const response = await api.get<AmountHoldNotice[]>("/holds/me");
    setHolds(response.data);
  };

  const recentPeople = useMemo(
    () => recentPeopleFromHistory(history?.items ?? [], 8),
    [history],
  );

  const latest = (history?.items ?? []).slice(0, 8);

  return (
    <div className="flex flex-1 flex-col gap-5">
      <PageHeader
        title="Home"
        description={
          user?.full_name
            ? `Welcome back, ${user.full_name.split(" ")[0]}.`
            : "Your balance and recent transfers."
        }
      />

      {restricted && (
        <section className="surface-card space-y-2 p-5">
          <h2 className="text-sm font-semibold">Outgoing transfers restricted</h2>
          <p className="text-sm text-[var(--color-text-muted)]">
            You cannot send money while this case is open. You can still receive money.
          </p>
        </section>
      )}
      {heldTransfers.map((item) => (
        <section key={item.transaction_id} className="surface-card space-y-2 p-5">
          <h2 className="text-sm font-semibold">Held for review</h2>
          <p className="text-sm text-[var(--color-text-muted)]">
            {item.amount} ST has not moved. You can still receive money. The rest of your balance
            stays available except for this reservation.
          </p>
        </section>
      ))}
      {holds.map((hold) => (
        <section key={hold.id} className="surface-card space-y-3 p-5">
          <h2 className="text-sm font-semibold">
            {hold.kind === "quarantine"
              ? "Quarantined amount"
              : hold.kind === "reservation"
                ? "Reserved for review"
                : "Amount on hold"}
          </h2>
          <p className="text-sm text-[var(--color-text-muted)]">
            {hold.amount} ST cannot be sent. You can still receive money.
            {hold.kind !== "quarantine" && hold.kind !== "reservation" && (
              <> Respond by {new Date(hold.explanation_due_at).toLocaleDateString()}.</>
            )}
          </p>
          {hold.narrative && <p className="text-sm text-pretty">{hold.narrative}</p>}
          {hold.user_explanation ? (
            <p className="text-sm">Your note: {hold.user_explanation}</p>
          ) : (
            <form
              className="space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                void submitExplanation(hold.id);
              }}
            >
              <label className="text-sm font-medium" htmlFor={`hold-note-${hold.id}`}>
                Explain this activity
              </label>
              <textarea
                id={`hold-note-${hold.id}`}
                className="input min-h-24"
                value={explanation}
                onChange={(event) => setExplanation(event.target.value)}
              />
              <Button type="submit">Send explanation</Button>
            </form>
          )}
        </section>
      ))}

      <div className="grid flex-1 gap-5 lg:grid-cols-12 lg:items-stretch lg:gap-6">
        <section className="surface-card flex flex-col shadow-[var(--shadow-md)] lg:col-span-5">
          <div className="flex flex-1 flex-col gap-6 p-5 sm:gap-8 sm:p-7">
            <div className="space-y-2">
              <p className="text-sm font-medium text-[var(--color-text-muted)]">Available balance</p>
              <div className="flex items-baseline gap-2.5">
                <SlotText
                  text={user?.balance ?? "—"}
                  className="text-[2.5rem] font-semibold leading-none tracking-tight tabular text-[var(--color-text)] sm:text-[2.75rem]"
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

            <div className="mt-auto pt-2">
              <Link to="/send" className="btn-primary w-full justify-center sm:w-auto sm:px-8">
                <SfIcon name="paperplane" weight="semibold" size={16} variant="fill" />
                Send money
              </Link>
            </div>
          </div>
        </section>

        <div className="flex min-h-0 flex-col gap-5 lg:col-span-7">
          <section className="space-y-3">
            <h2 className="text-sm font-semibold tracking-tight text-[var(--color-text-muted)]">
              Recent people
            </h2>
            {loadingHistory && <p className="text-sm text-[var(--color-text-muted)]">Loading…</p>}
            {!loadingHistory && recentPeople.length === 0 && (
              <EmptyState
                title="No recent recipients yet"
                description="Send money once and they’ll show up here for one-tap pay again."
                symbol="paperplane"
                action={
                  <Button onClick={() => navigate("/send")} className="sm:!w-auto">
                    Send your first transfer
                  </Button>
                }
              />
            )}
            {recentPeople.length > 0 && (
              <ul className="flex gap-2 overflow-x-auto pb-0.5 sm:gap-3">
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
                      className="flex w-[4.5rem] flex-col items-center gap-1.5 rounded-[var(--radius-lg)] p-1.5 transition-[transform,background-color] duration-150 ease-[cubic-bezier(0.2,0,0,1)] hover:bg-[var(--color-accent-soft)] active:scale-[0.96] sm:w-20 sm:p-2"
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

          <section className="flex min-h-0 flex-1 flex-col gap-3">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold tracking-tight text-[var(--color-text-muted)]">
                Latest activity
              </h2>
              <Link
                to="/activity"
                className="text-xs font-semibold text-[var(--color-accent)] underline-offset-2 hover:underline"
              >
                See all
              </Link>
            </div>
            <ul className="surface-card flex-1 divide-y divide-[var(--color-border)] overflow-hidden">
              {latest.map((tx) => (
                <li key={tx.transaction_id}>
                  <button
                    type="button"
                    onClick={() => navigate(`/activity/${tx.transaction_id}`)}
                    className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-[var(--color-accent-soft)] sm:px-5"
                  >
                    <Avatar name={tx.counterparty_name} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold">{tx.counterparty_name}</p>
                      <p className="text-xs text-[var(--color-text-muted)]">
                        {formatWhen(tx.created_at)}
                      </p>
                    </div>
                    <Amount value={tx.amount} signed direction={tx.direction} size="sm" />
                  </button>
                </li>
              ))}
              {!loadingHistory && latest.length === 0 && (
                <li className="px-4 py-8 text-center text-sm text-[var(--color-text-muted)]">
                  No transactions yet.
                </li>
              )}
            </ul>
          </section>
        </div>
      </div>
    </div>
  );
}
