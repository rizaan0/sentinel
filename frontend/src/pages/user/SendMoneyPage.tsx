import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import { extractErrorMessage } from "../../lib/errors";
import type { RecipientResult, TransactionReceipt } from "../../lib/types";
import { useAuth } from "../../lib/useAuth";

type Step = "search" | "amount" | "review" | "receipt";

/**
 * Send Money wizard: search -> select -> amount/remark -> review -> PIN
 * authorization -> receipt (per idea.md's described transfer flow).
 */
export default function SendMoneyPage() {
  const { refreshUser } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState<Step>("search");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [accountNumber, setAccountNumber] = useState("");
  const [recipient, setRecipient] = useState<RecipientResult | null>(null);

  const [amount, setAmount] = useState("");
  const [remark, setRemark] = useState("");
  const [pin, setPin] = useState("");

  const [receipt, setReceipt] = useState<TransactionReceipt | null>(null);

  const onSearch = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const response = await api.get<RecipientResult>("/transactions/search", {
        params: { account_number: accountNumber },
      });
      setRecipient(response.data);
      setStep("amount");
    } catch (err) {
      setError(extractErrorMessage(err, "No account found with that number."));
    } finally {
      setSubmitting(false);
    }
  };

  const onContinueToReview = (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    const parsed = Number(amount);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setError("Enter a valid amount greater than zero.");
      return;
    }
    setStep("review");
  };

  const onAuthorize = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const response = await api.post<TransactionReceipt>("/transactions/transfer", {
        recipient_account_number: recipient!.account_number,
        amount,
        remark: remark || null,
        pin,
      });
      setReceipt(response.data);
      setStep("receipt");
      await refreshUser();
    } catch (err) {
      setError(extractErrorMessage(err, "Transfer failed."));
    } finally {
      setSubmitting(false);
      setPin("");
    }
  };

  return (
    <main className="min-h-screen p-6 max-w-md mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Send money</h1>
        <Link to="/dashboard" className="text-sm underline text-neutral-500">
          Back to dashboard
        </Link>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {step === "search" && (
        <form onSubmit={onSearch} className="space-y-4">
          <label className="block text-sm font-medium">
            Recipient account number
            <input
              required
              value={accountNumber}
              onChange={(e) => setAccountNumber(e.target.value)}
              className="input mt-1"
              placeholder="e.g. 123456789012"
            />
          </label>
          <button type="submit" disabled={submitting} className="btn-primary w-full">
            {submitting ? "Searching..." : "Find recipient"}
          </button>
        </form>
      )}

      {step === "amount" && recipient && (
        <form onSubmit={onContinueToReview} className="space-y-4">
          <RecipientCard recipient={recipient} />
          <label className="block text-sm font-medium">
            Amount (ST)
            <input
              required
              type="number"
              min="0.01"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="input mt-1"
            />
          </label>
          <label className="block text-sm font-medium">
            Remark (optional)
            <input
              value={remark}
              onChange={(e) => setRemark(e.target.value)}
              maxLength={280}
              className="input mt-1"
            />
          </label>
          <button type="submit" className="btn-primary w-full">
            Review transfer
          </button>
        </form>
      )}

      {step === "review" && recipient && (
        <form onSubmit={onAuthorize} className="space-y-4">
          <RecipientCard recipient={recipient} />
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-4 space-y-1 text-sm">
            <Row label="Amount" value={`${amount} ST`} />
            {remark && <Row label="Remark" value={remark} />}
          </div>
          <label className="block text-sm font-medium">
            Enter Transaction PIN to authorize
            <input
              required
              inputMode="numeric"
              type="password"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              className="input mt-1"
            />
          </label>
          <button type="submit" disabled={submitting} className="btn-primary w-full">
            {submitting ? "Processing..." : "Authorize transfer"}
          </button>
        </form>
      )}

      {step === "receipt" && receipt && (
        <div className="space-y-4">
          <div className="rounded-lg border border-green-300 dark:border-green-800 bg-green-50 dark:bg-green-950 p-4 space-y-2">
            <p className="font-semibold text-green-700 dark:text-green-400">Transfer successful</p>
            <Row label="Transaction ID" value={receipt.transaction_id} mono />
            <Row label="To" value={`${receipt.receiver_name} (${receipt.receiver_account_number})`} />
            <Row label="Amount" value={`${receipt.amount} ST`} />
            {receipt.remark && <Row label="Remark" value={receipt.remark} />}
            <Row label="New balance" value={`${receipt.balance_after} ST`} />
          </div>
          <button onClick={() => navigate("/dashboard")} className="btn-primary w-full">
            Back to dashboard
          </button>
        </div>
      )}
    </main>
  );
}

function RecipientCard({ recipient }: { recipient: RecipientResult }) {
  return (
    <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-4">
      <p className="text-sm text-neutral-500">Sending to</p>
      <p className="font-medium">{recipient.full_name}</p>
      <p className="font-mono text-sm">{recipient.account_number}</p>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-neutral-500">{label}</span>
      <span className={mono ? "font-mono text-right" : "text-right"}>{value}</span>
    </div>
  );
}
