import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/useAuth";
import { extractErrorMessage } from "../../lib/errors";
import { AuthLayout } from "../../components/ui/AuthLayout";
import { Button } from "../../components/ui/Button";
import { Field } from "../../components/ui/Field";
import { Input } from "../../components/ui/Input";
import { InlineAlert } from "../../components/ui/InlineAlert";

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await signup(fullName, email, password);
      navigate("/pin-setup", { replace: true });
    } catch (err: unknown) {
      setError(extractErrorMessage(err, "Could not create account."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Get a unique account number and 1000 ST Coins to start."
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field label="Full name" htmlFor="signup-name">
          <Input
            id="signup-name"
            required
            autoComplete="name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
        </Field>
        <Field label="Email" htmlFor="signup-email">
          <Input
            id="signup-email"
            required
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            invalid={Boolean(error)}
          />
        </Field>
        <Field
          label="Password"
          htmlFor="signup-password"
          hint="At least 8 characters."
        >
          <Input
            id="signup-password"
            required
            type="password"
            autoComplete="new-password"
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field>

        {error && <InlineAlert>{error}</InlineAlert>}

        <Button type="submit" disabled={submitting} fullWidth>
          {submitting ? "Creating account…" : "Sign up"}
        </Button>

        <p className="text-center text-sm text-[var(--color-text-muted)]">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-[var(--color-accent)] underline-offset-2 hover:underline">
            Log in
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}
