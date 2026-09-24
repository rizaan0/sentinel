import { SlotText } from "slot-text/react";
import { useAuth } from "../../lib/useAuth";
import { cue } from "../../lib/cue";
import { LiquidCard, LiquidGroup } from "../../liquid/LiquidGroup";
import { AccountNumber } from "../../components/ui/AccountNumber";
import { Avatar } from "../../components/ui/Avatar";
import { Button } from "../../components/ui/Button";
import { PageHeader } from "../../components/ui/PageHeader";
import { SfIcon } from "../../components/ui/icons";

/** Virtual design space for fused profile cards (liquidui geometric mode). */
const VW = 720;
const VH = 200;

function IdentityBody() {
  const { user } = useAuth();
  return (
    <div className="flex h-full items-center gap-4 p-5 sm:p-6">
      <Avatar name={user?.full_name ?? "User"} size="lg" />
      <div className="min-w-0">
        <p className="truncate text-lg font-semibold tracking-tight">{user?.full_name}</p>
        <p className="truncate text-sm text-[var(--color-text-muted)]">{user?.email}</p>
      </div>
    </div>
  );
}

function DetailsBody() {
  const { user } = useAuth();
  return (
    <div className="divide-y divide-[var(--color-border)] text-sm">
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
    </div>
  );
}

export default function ProfilePage() {
  const { logout } = useAuth();

  return (
    <div className="flex flex-1 flex-col gap-5">
      <PageHeader
        title="Profile"
        description="Your Sentinel identity and account details."
      />

      {/* Mobile: stacked cards — fusion needs a fixed adjacent layout */}
      <div className="grid gap-5 lg:hidden">
        <section className="surface-card">
          <IdentityBody />
        </section>
        <section className="surface-card">
          <DetailsBody />
        </section>
      </div>

      {/* Desktop: liquidui soft-min join between identity + details */}
      <div className="relative hidden w-full lg:block" style={{ aspectRatio: `${VW} / ${VH}` }}>
        <div className="absolute inset-0" style={{ containerType: "size" }}>
          <div
            className="absolute left-1/2 top-1/2"
            style={{
              width: VW,
              height: VH,
              transform: "translate(-50%, -50%)",
              transformOrigin: "center",
              scale: `calc(100cqw / ${VW})`,
            }}
          >
            <LiquidGroup
              k={22}
              cell={5}
              smooth={2}
              cardRadius={24}
              bridges={[{ from: "identity", to: "details", width: 56 }]}
              fill="var(--color-surface-raised)"
              fillStyle={{
                filter: "drop-shadow(0 1px 2px oklch(0.229 0.055 264.481 / 0.04))",
              }}
              className="h-full w-full"
            >
              <LiquidCard id="identity" x={0} y={24} w={290} h={128} radius={24}>
                <IdentityBody />
              </LiquidCard>
              <LiquidCard id="details" x={310} y={8} w={410} h={184} radius={24}>
                <DetailsBody />
              </LiquidCard>
            </LiquidGroup>
          </div>
        </div>
      </div>

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
  );
}
