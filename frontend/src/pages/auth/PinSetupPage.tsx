import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/useAuth";
import { extractErrorMessage } from "../../lib/errors";
import { AuthLayout } from "../../components/ui/AuthLayout";
import { Button } from "../../components/ui/Button";
import { Field } from "../../components/ui/Field";
import { Input } from "../../components/ui/Input";
import { InlineAlert } from "../../components/ui/InlineAlert";

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
      setError("PIN must be 4–6 digits.");
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
    <AuthLayout
      title="Create your Transaction PIN"
      subtitle="This PIN authorizes every transfer — separate from your login password."
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field label="PIN (4-6 digits)" htmlFor="pin-setup" hint="Digits only. Never share this PIN.">
          <Input
            id="pin-setup"
            required
            inputMode="numeric"
            autoComplete="one-time-code"
            type="password"
            maxLength={6}
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
            className="tracking-[0.4em] text-center text-lg"
            invalid={Boolean(error)}
          />
        </Field>
        <Field label="Confirm PIN" htmlFor="pin-confirm">
          <Input
            id="pin-confirm"
            required
            inputMode="numeric"
            autoComplete="one-time-code"
            type="password"
            maxLength={6}
            value={confirmPin}
            onChange={(e) => setConfirmPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
            className="tracking-[0.4em] text-center text-lg"
            invalid={Boolean(error)}
          />
        </Field>

        {error && <InlineAlert>{error}</InlineAlert>}

        <Button type="submit" disabled={submitting} fullWidth>
          {submitting ? "Saving…" : "Set PIN"}
        </Button>
      </form>
    </AuthLayout>
  );
}
