import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { chromatic } from "slot-text";
import { SlotText } from "slot-text/react";
import { api } from "../../lib/api";
import { cue } from "../../lib/cue";
import { extractErrorMessage } from "../../lib/errors";
import type { AmountHoldNotice, PaginatedTransactions, RecipientResult, TransactionReceipt } from "../../lib/types";
import { useAuth } from "../../lib/useAuth";
import { recentPeopleFromHistory } from "../../lib/recentPeople";
import { AccountNumber } from "../../components/ui/AccountNumber";
import { Amount } from "../../components/ui/Amount";
import { Avatar } from "../../components/ui/Avatar";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Field } from "../../components/ui/Field";
import { InlineAlert } from "../../components/ui/InlineAlert";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { PageHeader } from "../../components/ui/PageHeader";
import { SfIcon } from "../../components/ui/icons";
import { Stepper } from "../../components/ui/Stepper";
import { TransactionId } from "../../components/ui/TransactionId";

type Step = "search" | "amount" | "review" | "receipt";

const STEPS = [
  { id: "search", label: "Find" },
  { id: "amount", label: "Amount" },
  { id: "review", label: "Review" },
  { id: "receipt", label: "Done" },
];

/**
 * Send Money wizard: find (recent + search) -> amount -> review -> PIN -> receipt.
 */
export default function SendMoneyPage() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const preselected = (location.state as { recipient?: RecipientResult } | null)?.recipient;

  const [step, setStep] = useState<Step>(preselected ? "amount" : "search");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RecipientResult[]>([]);
  const [recipient, setRecipient] = useState<RecipientResult | null>(preselected ?? null);
  const [recent, setRecent] = useState<RecipientResult[]>([]);

  const [amount, setAmount] = useState("");
  const [remark, setRemark] = useState("");
  const [pin, setPin] = useState("");
  const [pinOpen, setPinOpen] = useState(false);

  const [receipt, setReceipt] = useState<TransactionReceipt | null>(null);

  const [held, setHeld] = useState(0);

  useEffect(() => {
    api
      .get<PaginatedTransactions>("/transactions/history", { params: { limit: 30 } })
      .then((response) => setRecent(recentPeopleFromHistory(response.data.items, 8)));
    api
      .get<AmountHoldNotice[]>("/holds/me")
      .then((response) => {
        const total = response.data.reduce((sum, hold) => sum + Number(hold.amount), 0);
        setHeld(total);
      })
      .catch(() => setHeld(0));
  }, []);

  const remaining = useMemo(() => {
    if (user?.balance == null) return null;
    const balance = Number(user.balance);
    const parsed = Number(amount);
    if (!Number.isFinite(balance) || !Number.isFinite(parsed)) return null;
    return balance - parsed;
  }, [user?.balance, amount]);

  const onSearch = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    const q = query.trim();
    if (!q) {
      cue.error();
      setError("Enter a name or account number.");
      return;
    }
    setSubmitting(true);
    cue.loading();
    try {
      const response = await api.get<RecipientResult[]>("/transactions/search", {
        params: { q },
      });
      setResults(response.data);
      if (response.data.length === 0) {
        cue.error();
        setError("No matching accounts found.");
      }
    } catch (err) {
      cue.error();
      setError(extractErrorMessage(err, "Search failed."));
      setResults([]);
    } finally {
      setSubmitting(false);
    }
  };

  const selectRecipient = (person: RecipientResult) => {
    setRecipient(person);
    setError(null);
    setStep("amount");
  };

  const onContinueToReview = (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    const parsed = Number(amount);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      cue.error();
      setError("Enter a valid amount greater than zero.");
      return;
    }
    if (remaining !== null && remaining < held) {
      cue.error();
      setError(
        held > 0
          ? `${held.toFixed(2)} ST is on hold after a risk review, so only ${Math.max(0, (Number(user?.balance) || 0) - held).toFixed(2)} ST can be sent. You can still receive money.`
          : "Amount exceeds your available balance.",
      );
      return;
    }
    setStep("review");
  };

  const [challenge, setChallenge] = useState<{
    challenge_id: string;
    code: string;
    reasons: string[];
    idempotency_key: string;
  } | null>(null);
  const [otp, setOtp] = useState("");

  const finishReceipt = async (receipt: TransactionReceipt) => {
    setReceipt(receipt);
    setPinOpen(false);
    setChallenge(null);
    setStep("receipt");
    cue.success("payment");
    await refreshUser();
  };

  const onAuthorize = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (!/^\d{4,6}$/.test(pin)) {
      cue.error();
      setError("Enter your 4–6 digit Transaction PIN.");
      return;
    }
    setSubmitting(true);
    cue.loading();
    const idempotencyKey = crypto.randomUUID();
    try {
      const response = await api.post<TransactionReceipt>("/transactions/transfer", {
        recipient_account_number: recipient!.account_number,
        amount,
        remark: remark || null,
        pin,
        idempotency_key: idempotencyKey,
      });
      if (response.status === 202) {
        setError("Held for review. The money has not moved. You can still receive money.");
        setPinOpen(false);
        cue.error();
        return;
      }
      await finishReceipt(response.data);
    } catch (err) {
      const response = (err as { response?: { status?: number; data?: { challenge_id?: string; code?: string; reasons?: string[]; detail?: string } } }).response;
      if (response?.status === 428 && response.data?.challenge_id && response.data.code) {
        setChallenge({
          challenge_id: response.data.challenge_id,
          code: response.data.code,
          reasons: response.data.reasons ?? [],
          idempotency_key: idempotencyKey,
        });
        setPinOpen(false);
        cue.success("payment");
        return;
      }
      cue.error();
      setError(extractErrorMessage(err, "Transfer failed."));
    } finally {
      setSubmitting(false);
      setPin("");
    }
  };

  const onConfirmCode = async (event: FormEvent) => {
    event.preventDefault();
    if (!challenge) return;
    setSubmitting(true);
    setError(null);
    try {
      const response = await api.post<TransactionReceipt>("/transactions/transfer/confirm", {
        challenge_id: challenge.challenge_id,
        code: otp,
        idempotency_key: challenge.idempotency_key,
      });
      await finishReceipt(response.data);
    } catch (err) {
      cue.error();
      setError(extractErrorMessage(err, "That code was not accepted."));
    } finally {
      setSubmitting(false);
    }
  };

  const goBack = () => {
    setError(null);
    if (step === "amount") setStep("search");
    else if (step === "review") setStep("amount");
  };

  return (
    <div className="flex flex-1 flex-col gap-5">
      <PageHeader
        title="Send money"
        description="Pay anyone on Sentinel with ST Coins."
      />

      {step !== "receipt" && (
        <div className="w-full max-w-3xl">
          <Stepper steps={STEPS} current={step} />
        </div>
      )}

      {error && step !== "review" && <InlineAlert>{error}</InlineAlert>}

      {step === "search" && (
        <div className="grid gap-5 lg:grid-cols-12 lg:items-start lg:gap-6">
          <div className="flex flex-col gap-5 lg:col-span-7">
            <form onSubmit={onSearch} className="space-y-3">
              <Field
                label="Search by name or account number"
                htmlFor="recipient-q"
                hint="Paste an account number or type part of a name."
              >
                <Input
                  id="recipient-q"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  autoComplete="off"
                  placeholder="e.g. Alex or 1234 5678…"
                />
              </Field>
              <Button type="submit" disabled={submitting} className="w-full sm:w-auto sm:min-w-40">
                <SfIcon name="magnifyingglass" weight="semibold" size={16} />
                {submitting ? "Searching…" : "Search"}
              </Button>
            </form>

            {results.length > 0 && (
              <ul className="surface-card divide-y divide-[var(--color-border)] overflow-hidden">
                {results.map((person) => (
                  <li key={person.account_number}>
                    <button
                      type="button"
                      onClick={() => selectRecipient(person)}
                      className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-[var(--color-ink-50)]"
                    >
                      <Avatar name={person.full_name} size="sm" />
                      <div className="min-w-0">
                        <p className="font-medium">{person.full_name}</p>
                        <AccountNumber
                          number={person.account_number}
                          copyable={false}
                          className="mt-0.5 text-[var(--color-text-muted)]"
                        />
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {recent.length === 0 && results.length === 0 && !submitting && (
              <EmptyState
                title="Find someone to pay"
                description="Search by their name or full account number. Recent people appear here after your first transfer."
                symbol="magnifyingglass"
              />
            )}
          </div>

          <aside className="lg:col-span-5">
            {recent.length > 0 ? (
              <section className="surface-card space-y-3 p-4 sm:p-5">
                <h2 className="text-sm font-semibold tracking-tight text-[var(--color-text-muted)]">
                  Recent
                </h2>
                <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4 lg:grid-cols-3">
                  {recent.map((person) => (
                    <li key={person.account_number}>
                      <button
                        type="button"
                        onClick={() => selectRecipient(person)}
                        className="flex w-full flex-col items-center gap-1.5 rounded-[var(--radius-lg)] p-2 transition-[transform,background-color] duration-150 ease-[cubic-bezier(0.2,0,0,1)] hover:bg-[var(--color-accent-soft)] active:scale-[0.96]"
                      >
                        <Avatar name={person.full_name} />
                        <span className="w-full truncate text-center text-xs font-medium">
                          {person.full_name.split(" ")[0]}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            ) : (
              <div className="hidden rounded-[var(--radius-xl)] border border-dashed border-[var(--color-border)] bg-[var(--color-surface-muted)] p-5 text-sm leading-relaxed text-[var(--color-text-muted)] lg:block">
                Recent recipients will appear here after your first transfer for one-tap send.
              </div>
            )}
          </aside>
        </div>
      )}

      {step === "amount" && recipient && (
        <form onSubmit={onContinueToReview} className="w-full max-w-xl space-y-4">
          <RecipientCard recipient={recipient} onChange={() => setStep("search")} />
          <div className="surface-inset space-y-3 p-5">
            <p className="label-accent">You&apos;re sending</p>
            <Field label="Amount (ST)" htmlFor="amount">
              <Input
                id="amount"
                required
                type="number"
                min="0.01"
                step="0.01"
                inputMode="decimal"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="!border-0 !bg-transparent text-center text-3xl font-extrabold tabular !ring-0 focus:!ring-0"
              />
            </Field>
            <p className="text-xs text-[var(--color-text-muted)]">
              Available:{" "}
              <SlotText
                text={`${user?.balance ?? "—"} ST`}
                className="tabular font-semibold text-[var(--color-text)]"
                options={{ duration: 200, stagger: 20 }}
              />
              {remaining !== null && Number.isFinite(remaining) && (
                <>
                  {" "}
                  · After:{" "}
                  <SlotText
                    text={`${remaining.toFixed(2)} ST`}
                    className="tabular font-semibold text-[var(--color-text)]"
                    options={{ duration: 200, stagger: 20 }}
                  />
                </>
              )}
            </p>
          </div>
          <Field label="Remark (optional)" htmlFor="remark">
            <Input
              id="remark"
              value={remark}
              onChange={(e) => setRemark(e.target.value)}
              maxLength={280}
            />
          </Field>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={goBack} fullWidth>
              Back
            </Button>
            <Button type="submit" fullWidth>
              Review
            </Button>
          </div>
        </form>
      )}

      {step === "review" && recipient && (
        <div className="w-full max-w-xl space-y-4">
          <RecipientCard recipient={recipient} onChange={() => setStep("search")} />
          <div className="surface-card space-y-2 p-4 text-sm">
            <Row label="Amount" value={`${amount} ST`} />
            {remark && <Row label="Remark" value={remark} />}
            <Row label="From balance" value={`${user?.balance} ST`} />
          </div>
          {error && <InlineAlert>{error}</InlineAlert>}
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={goBack} fullWidth>
              Back
            </Button>
            <Button type="button" onClick={() => setPinOpen(true)} fullWidth>
              <SfIcon name="lock" weight="semibold" size={16} />
              Confirm & enter PIN
            </Button>
          </div>

          <Modal
            open={pinOpen}
            title="Authorize transfer"
            onClose={() => {
              setPinOpen(false);
              setPin("");
              setError(null);
            }}
            footer={
              <Button type="submit" form="pin-form" disabled={submitting} fullWidth>
                <SlotText
                  text={submitting ? "Processing…" : `Pay ${amount} ST`}
                  options={{ rollBy: "word", duration: 200, stagger: 24 }}
                />
              </Button>
            }
          >
            <form id="pin-form" onSubmit={onAuthorize} className="space-y-3">
              <p className="text-sm text-[var(--color-text-muted)]">
                Enter your Transaction PIN to send{" "}
                <span className="font-semibold text-[var(--color-text)]">{amount} ST</span> to{" "}
                <span className="font-semibold text-[var(--color-text)]">{recipient.full_name}</span>.
              </p>
              <Field label="Transaction PIN" htmlFor="transfer-pin">
                <Input
                  id="transfer-pin"
                  required
                  inputMode="numeric"
                  type="password"
                  autoComplete="one-time-code"
                  maxLength={6}
                  value={pin}
                  onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  className="tracking-[0.4em] text-center text-lg"
                  invalid={Boolean(error)}
                />
              </Field>
              {error && <InlineAlert>{error}</InlineAlert>}
            </form>
          </Modal>
          <Modal
            open={Boolean(challenge)}
            title="Confirm this transfer"
            onClose={() => setChallenge(null)}
            footer={
              <Button type="submit" form="otp-form" disabled={submitting} fullWidth>
                Confirm code
              </Button>
            }
          >
            {challenge && (
              <form id="otp-form" onSubmit={onConfirmCode} className="space-y-3">
                <p className="text-sm text-[var(--color-text-muted)]">
                  This transfer scored high risk. Enter the code shown here. It confirms the person
                  at this screen. It is not a text-message code.
                </p>
                <p className="text-center text-2xl font-semibold tracking-[0.3em]">{challenge.code}</p>
                {challenge.reasons.length > 0 && (
                  <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--color-text-muted)]">
                    {challenge.reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                )}
                <Field label="Code" htmlFor="transfer-otp">
                  <Input
                    id="transfer-otp"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    value={otp}
                    onChange={(event) => setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))}
                  />
                </Field>
                {error && <InlineAlert>{error}</InlineAlert>}
              </form>
            )}
          </Modal>
        </div>
      )}

      {step === "receipt" && receipt && (
        <div className="w-full max-w-xl space-y-4">
          <div className="surface-card space-y-4 bg-[var(--color-accent-soft)] p-5 text-center">
            <p className="text-sm font-bold text-[var(--color-accent)]">
              <SlotText
                text="Transfer successful"
                options={{
                  rollBy: "word",
                  direction: "up",
                  color: chromatic({ from: 200 }),
                  duration: 240,
                  stagger: 40,
                }}
              />
            </p>
            <Amount value={receipt.amount} size="xl" />
            <p className="text-sm text-[var(--color-text-muted)]">
              to {receipt.receiver_name}
            </p>
          </div>
          <div className="surface-card divide-y divide-[var(--color-border)] text-sm">
            <div className="flex items-center justify-between gap-3 px-4 py-3">
              <span className="shrink-0 text-[var(--color-text-muted)]">Reference</span>
              <TransactionId id={receipt.transaction_id} />
            </div>
            <Row label="New balance" value={`${receipt.balance_after} ST`} />
            {receipt.remark && <Row label="Remark" value={receipt.remark} />}
          </div>
          <Button onClick={() => navigate("/dashboard")} fullWidth>
            Done
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setStep("amount");
              setAmount("");
              setRemark("");
              setReceipt(null);
            }}
            fullWidth
          >
            Pay again
          </Button>
        </div>
      )}
    </div>
  );
}

function RecipientCard({
  recipient,
  onChange,
}: {
  recipient: RecipientResult;
  onChange?: () => void;
}) {
  return (
    <div className="surface-card flex items-center gap-3 p-4">
      <Avatar name={recipient.full_name} />
      <div className="min-w-0 flex-1">
        <p className="text-xs text-[var(--color-text-muted)]">Sending to</p>
        <p className="truncate font-medium">{recipient.full_name}</p>
        <AccountNumber number={recipient.account_number} copyable={false} />
      </div>
      {onChange && (
        <Button variant="ghost" onClick={onChange} className="!min-h-10 text-xs">
          Change
        </Button>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 px-4 py-3">
      <span className="text-[var(--color-text-muted)]">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  );
}
