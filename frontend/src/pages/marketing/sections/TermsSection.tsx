import { LANDING_FRAME, LANDING_PAD } from "../landingRail";

export default function TermsSection() {
  return (
    <section id="terms" className={`${LANDING_PAD} scroll-mt-32 pb-16`}>
      <div className={LANDING_FRAME}>
        <div className="max-w-xl">
        <h2 className="text-sm font-medium text-[var(--color-text)]">Terms</h2>
        <div className="mt-4 space-y-3 text-sm leading-6 text-[var(--color-text-muted)]">
          <p>Sentinel lets you send and receive ST Coins inside this app.</p>
          <p>You are responsible for the account you create and the transfers you send.</p>
          <p>
            Every transfer is scored. Sentinel may ask you to confirm a transfer, or hold only the
            flagged amount, when the risk rules say so. Incoming transfers are not blocked.
          </p>
        </div>
        </div>
      </div>
    </section>
  );
}