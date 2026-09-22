import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/useAuth";
import { extractErrorMessage } from "../../lib/errors";
import { AuthLayout } from "../../components/ui/AuthLayout";
import { Button } from "../../components/ui/Button";
import { Field } from "../../components/ui/Field";
import { Input } from "../../components/ui/Input";
import { InlineAlert } from "../../components/ui/InlineAlert";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await login(email, password);
      if (user.role === "admin") {
        navigate("/admin", { replace: true });
      } else {
        navigate(user.pin_is_set ? "/dashboard" : "/pin-setup", { replace: true });
      }
    } catch (err: unknown) {
      setError(extractErrorMessage(err, "Incorrect email or password."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout title="Welcome back" subtitle="Log in to send ST Coins and manage your account.">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field label="Email" htmlFor="login-email" error={error ? undefined : undefined}>
          <Input
            id="login-email"
            required
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            invalid={Boolean(error)}
          />
        </Field>
        <Field label="Password" htmlFor="login-password">
          <Input
            id="login-password"
            required
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            invalid={Boolean(error)}
          />
        </Field>

        {error && <InlineAlert>{error}</InlineAlert>}

        <Button type="submit" disabled={submitting} fullWidth>
          {submitting ? "Logging in…" : "Log in"}
        </Button>

        <p className="text-center text-sm text-[var(--color-text-muted)]">
          Don&apos;t have an account?{" "}
          <Link to="/signup" className="font-medium text-[var(--color-accent)] underline-offset-2 hover:underline">
            Sign up
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}
