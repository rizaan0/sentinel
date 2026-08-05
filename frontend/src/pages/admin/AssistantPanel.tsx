import { useState, type FormEvent } from "react";
import { api } from "../../lib/api";
import type { AssistantLogEntry } from "../../lib/adminTypes";
import { extractErrorMessage } from "../../lib/errors";

interface AssistantPanelProps {
  transactionId?: string;
  accountNumber?: string;
}

/**
 * AI Investigation Assistant chat panel, embedded in an alert/user detail
 * view. It only explains monitoring results (rules, ML score,
 * reconciliation) - it never decides fraud (per idea.md and the
 * Architecture Rules).
 */
export default function AssistantPanel({ transactionId, accountNumber }: AssistantPanelProps) {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<AssistantLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const response = await api.post<AssistantLogEntry>("/assistant/ask", {
        question,
        transaction_id: transactionId,
        account_number: transactionId ? undefined : accountNumber,
      });
      setHistory((prev) => [...prev, response.data]);
      setQuestion("");
    } catch (err) {
      setError(extractErrorMessage(err, "The AI Investigation Assistant is unavailable."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mt-3 border-t border-neutral-200 dark:border-neutral-800 pt-3 space-y-2">
      <p className="text-xs font-medium text-neutral-500">AI Investigation Assistant</p>

      {history.map((entry) => (
        <div key={entry.id} className="text-sm space-y-1">
          <p className="font-medium">Q: {entry.question}</p>
          <p className="text-neutral-600 dark:text-neutral-300 whitespace-pre-wrap">
            {entry.answer}
          </p>
        </div>
      ))}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask why this was flagged..."
          className="input flex-1 text-sm"
          required
        />
        <button type="submit" disabled={submitting} className="btn-primary text-sm">
          {submitting ? "Asking..." : "Ask"}
        </button>
      </form>
    </div>
  );
}
