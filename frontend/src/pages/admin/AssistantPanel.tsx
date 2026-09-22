import { useState, type FormEvent } from "react";
import { api } from "../../lib/api";
import type { AssistantLogEntry } from "../../lib/adminTypes";
import { extractErrorMessage } from "../../lib/errors";
import { Button } from "../../components/ui/Button";
import { InlineAlert } from "../../components/ui/InlineAlert";
import { Input } from "../../components/ui/Input";

interface AssistantPanelProps {
  transactionId?: string;
  accountNumber?: string;
}

/**
 * AI Investigation Assistant — explains monitoring results only.
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
    <div className="space-y-3 border-t border-[var(--color-border)] pt-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
        AI Investigation Assistant
      </p>
      <p className="text-xs text-[var(--color-text-muted)]">
        Explains monitoring results — never decides fraud on its own.
      </p>

      {history.map((entry) => (
        <div key={entry.id} className="space-y-1 rounded-[var(--radius-md)] bg-[var(--color-ink-50)] p-3 text-sm">
          <p className="font-medium">Q: {entry.question}</p>
          <p className="whitespace-pre-wrap text-[var(--color-ink-700)] text-pretty">{entry.answer}</p>
        </div>
      ))}

      {error && <InlineAlert>{error}</InlineAlert>}

      <form onSubmit={onSubmit} className="flex gap-2">
        <label htmlFor="assistant-q" className="sr-only">
          Ask the investigation assistant
        </label>
        <Input
          id="assistant-q"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask why this was flagged…"
          className="!py-2 text-sm flex-1"
          required
        />
        <Button type="submit" disabled={submitting} className="!min-h-11 shrink-0">
          {submitting ? "…" : "Ask"}
        </Button>
      </form>
    </div>
  );
}
