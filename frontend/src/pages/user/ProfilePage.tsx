import { useAuth } from "../../lib/useAuth";
import { Avatar } from "../../components/ui/Avatar";
import { Button } from "../../components/ui/Button";
import { CopyButton } from "../../components/ui/CopyButton";

export default function ProfilePage() {
  const { user, logout } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Profile</h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Your Sentinel identity and account details.
        </p>
      </div>

      <section className="surface-card flex items-center gap-4 p-5">
        <Avatar name={user?.full_name ?? "User"} size="lg" />
        <div className="min-w-0">
          <p className="truncate text-lg font-semibold">{user?.full_name}</p>
          <p className="truncate text-sm text-[var(--color-text-muted)]">{user?.email}</p>
        </div>
      </section>

      <section className="surface-card divide-y divide-[var(--color-border)] text-sm">
        <div className="flex items-center justify-between gap-3 px-4 py-3">
          <div>
            <p className="text-[var(--color-text-muted)]">Account number</p>
            <p className="mt-0.5 font-mono font-medium">{user?.account_number}</p>
          </div>
          {user?.account_number && <CopyButton value={user.account_number} />}
        </div>
        <div className="px-4 py-3">
          <p className="text-[var(--color-text-muted)]">Balance</p>
          <p className="mt-0.5 tabular text-lg font-semibold">{user?.balance} ST</p>
        </div>
        <div className="px-4 py-3">
          <p className="text-[var(--color-text-muted)]">Transaction PIN</p>
          <p className="mt-0.5 font-medium">
            {user?.pin_is_set ? "Set" : "Not set"}
          </p>
        </div>
      </section>

      <Button variant="secondary" onClick={logout} fullWidth>
        Log out
      </Button>
    </div>
  );
}
