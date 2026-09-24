import { SlotText } from "slot-text/react";
import { useAuth } from "../../lib/useAuth";
import { cue } from "../../lib/cue";
import { AccountNumber } from "../../components/ui/AccountNumber";
import { Avatar } from "../../components/ui/Avatar";
import { Button } from "../../components/ui/Button";
import { PageHeader } from "../../components/ui/PageHeader";
import { SfIcon } from "../../components/ui/icons";

export default function ProfilePage() {
  const { user, logout } = useAuth();

  return (
    <div className="flex flex-1 flex-col gap-5">
      <PageHeader
        title="Profile"
        description="Your Sentinel identity and account details."
      />

      <div className="grid gap-5 lg:grid-cols-12 lg:items-start lg:gap-6">
        <section className="surface-card flex items-center gap-4 p-5 sm:p-6 lg:col-span-5">
          <Avatar name={user?.full_name ?? "User"} size="lg" />
          <div className="min-w-0">
            <p className="truncate text-lg font-semibold tracking-tight">{user?.full_name}</p>
            <p className="truncate text-sm text-[var(--color-text-muted)]">{user?.email}</p>
          </div>
        </section>

        <div className="flex flex-col gap-5 lg:col-span-7">
          <section className="surface-card divide-y divide-[var(--color-border)] text-sm">
            <div className="space-y-1.5 px-4 py-3.5 sm:px-5">
              <p className="text-[var(--color-text-muted)]">Your account</p>
              {user?.account_number && <AccountNumber number={user.account_number} />}
            </div>
            <div className="space-y-1.5 px-4 py-3.5 sm:px-5">
              <p className="text-[var(--color-text-muted)]">Balance</p>
              <div className="flex items-baseline gap-1.5">
                <SlotText
                  text={user?.balance ?? "—"}
                  className="tabular text-lg font-semibold"
                  options={{ duration: 220, stagger: 24 }}
                />
                <span className="text-sm font-medium text-[var(--color-text-muted)]">ST</span>
              </div>
            </div>
            <div className="space-y-1.5 px-4 py-3.5 sm:px-5">
              <p className="text-[var(--color-text-muted)]">Transaction PIN</p>
              <SlotText
                text={user?.pin_is_set ? "Set" : "Not set"}
                className="inline-block font-medium"
                options={{ rollBy: "word", duration: 220, stagger: 30 }}
              />
            </div>
          </section>

          <Button
            variant="secondary"
            onClick={() => {
              cue.dismiss();
              logout();
            }}
            className="w-full self-start sm:w-auto sm:min-w-40"
          >
            <SfIcon name="person.crop.circle" weight="semibold" size={16} />
            Log out
          </Button>
        </div>
      </div>
    </div>
  );
}
