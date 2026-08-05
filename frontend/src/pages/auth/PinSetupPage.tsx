import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/useAuth";
import { extractErrorMessage } from "../../lib/errors";

/**
 * Mandatory, one-time Transaction PIN setup, enforced by RequireAuth before
 * any other authenticated route is reachable (per idea.md).
 */
export default function PinSetupPage() {
  const { refreshUser } = useAuth();
  const navigate = useNavigate();

  const [pin, setPin] = useState("");
  const [confirmPin, setConfirmPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    if (pin !== confirmPin) {
      setError("PINs do not match.");
      return;
    }
    if (!/^\d{4,6}$/.test(pin)) {
      setError("PIN must be 4-6 digits.");
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/pin/setup", { pin });
      await refreshUser();
      navigate("/dashboard", { replace: true });
    } catch (err: unknown) {
      setError(extractErrorMessage(err, "Could not set PIN."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center bg-neutral-50 dark:bg-neutral-950">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm p-6 border rounded-lg border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 space-y-4"
      >
        <h1 className="text-xl font-semibold">Create your Transaction PIN</h1>
        <p className="text-sm text-neutral-500">
          This PIN authorizes every transfer you make, similar to a UPI PIN. It is stored
          securely and is separate from your login password.
        </p>

        <label className="block text-sm font-medium">
          PIN (4-6 digits)
          <input
            required
            inputMode="numeric"
            type="password"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            className="input mt-1"
          />
        </label>
        <label className="block text-sm font-medium">
          Confirm PIN
          <input
            required
            inputMode="numeric"
            type="password"
            value={confirmPin}
            onChange={(e) => setConfirmPin(e.target.value)}
            className="input mt-1"
          />
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button type="submit" disabled={submitting} className="btn-primary w-full">
          {submitting ? "Saving..." : "Set PIN"}
        </button>
      </form>
    </main>
  );
}
