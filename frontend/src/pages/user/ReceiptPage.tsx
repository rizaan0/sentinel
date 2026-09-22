import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../../lib/api";
import type { TransactionReceipt } from "../../lib/types";
import { extractErrorMessage } from "../../lib/errors";
import { formatWhen } from "../../lib/recentPeople";
import { AccountNumber } from "../../components/ui/AccountNumber";
import { Amount } from "../../components/ui/Amount";
import { Avatar } from "../../components/ui/Avatar";
import { Button } from "../../components/ui/Button";
import { InlineAlert } from "../../components/ui/InlineAlert";
import { TransactionId } from "../../components/ui/TransactionId";

export default function ReceiptPage() {
  const { transactionId } = useParams<{ transactionId: string }>();
  const navigate = useNavigate();
  const [receipt, setReceipt] = useState<TransactionReceipt | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!transactionId) return;
    api
      .get<TransactionReceipt>(`/transactions/${transactionId}`)
      .then((response) => setReceipt(response.data))
      .catch((err) => setError(extractErrorMessage(err, "Could not load receipt.")));
  }, [transactionId]);

  if (error) {
    return (
      <div className="space-y-4">
        <InlineAlert>{error}</InlineAlert>
        <Button variant="secondary" onClick={() => navigate("/activity")} fullWidth>
          Back to activity
        </Button>
      </div>
    );
  }

  if (!receipt) {
    return <p className="text-sm text-[var(--color-text-muted)]">Loading receipt…</p>;
  }

  const counterpartyName =
    receipt.direction === "sent" ? receipt.receiver_name : receipt.sender_name;
  const counterpartyAccount =
    receipt.direction === "sent"
      ? receipt.receiver_account_number
      : receipt.sender_account_number;

  return (
    <div className="space-y-5">
      <Link
        to="/activity"
        className="text-sm font-medium text-[var(--color-accent)] underline-offset-2 hover:underline"
      >
        ← Activity
      </Link>

      <div className="surface-card space-y-5 p-5 text-center">
        <Avatar name={counterpartyName} size="lg" />
        <div>
          <p className="text-sm text-[var(--color-text-muted)]">
            {receipt.direction === "sent" ? "Sent to" : "Received from"}
          </p>
          <p className="mt-1 text-lg font-semibold">{counterpartyName}</p>
          <div className="mt-2 flex justify-center">
            <AccountNumber number={counterpartyAccount} copyable={false} />
          </div>
        </div>
        <Amount value={receipt.amount} signed direction={receipt.direction} size="xl" />
        <p className="text-xs text-[var(--color-text-muted)]">{formatWhen(receipt.created_at)}</p>
      </div>

      <dl className="surface-card divide-y divide-[var(--color-border)] text-sm">
        <div className="flex items-center justify-between gap-3 px-4 py-3">
          <dt className="shrink-0 text-[var(--color-text-muted)]">Reference</dt>
          <dd className="min-w-0">
            <TransactionId id={receipt.transaction_id} />
          </dd>
        </div>
        <Row label="Status" value={receipt.status.replace("_", " ")} />
        {receipt.remark && <Row label="Remark" value={receipt.remark} />}
        <Row label="Balance after" value={`${receipt.balance_after} ST`} />
      </dl>

      <div className="flex flex-col gap-2">
        {receipt.direction === "sent" && (
          <Button
            onClick={() =>
              navigate("/send", {
                state: {
                  recipient: {
                    account_number: counterpartyAccount,
                    full_name: counterpartyName,
                  },
                },
              })
            }
            fullWidth
          >
            Pay again
          </Button>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 px-4 py-3">
      <dt className="text-[var(--color-text-muted)]">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  );
}
