import { LANDING_CONTENT } from "../landingRail";

export default function HeroSection() {
  return (
    <section className="relative flex flex-1 flex-col justify-center">
      <div className={`${LANDING_CONTENT} flex w-full flex-col items-center gap-12 py-8 sm:py-10`}>
        <div className="mx-auto flex w-fit max-w-full flex-col items-center pt-12 text-center">
          <div className="relative w-fit max-w-full">
            <h1 className="text-balance text-[2.25rem] font-semibold leading-[1.1] tracking-[-0.025em] text-[var(--color-text)] sm:text-[3rem] sm:leading-[1.05] md:text-[3.25rem]">
              Instant payments.
              <br />
              Always monitored.
            </h1>
            <HeadingSelection />
          </div>

          <p className="mt-12 w-0 min-w-full text-balance text-[0.9375rem] font-normal leading-[1.5] text-[var(--color-text-muted)] sm:text-base sm:leading-[1.6]">
            Send ST Coins like a wallet. Every transfer is scored for fraud in real time.
          </p>
        </div>

        <div className="w-full max-w-[21.5rem]">
          <div className="rounded-[20px] border border-[var(--color-border)] bg-white p-1.5 shadow-[var(--shadow-md)]">
            <div className="flex gap-1 rounded-[var(--radius-pill)] bg-[var(--color-surface-muted)] p-1 text-xs font-medium">
              <span className="flex-1 rounded-[var(--radius-pill)] bg-white px-3 py-1.5 text-[var(--color-accent)] shadow-[var(--shadow-sm)]">
                Send
              </span>
              <span className="flex-1 px-3 py-1.5 text-[var(--color-text-muted)]">Activity</span>
              <span className="flex-1 px-3 py-1.5 text-[var(--color-text-muted)]">Profile</span>
            </div>
            <div className="mt-1.5 space-y-1.5 p-2.5">
              <div className="rounded-[12px] bg-[var(--color-surface-muted)] px-3.5 py-3 text-left">
                <p className="text-sm font-medium text-[var(--color-accent)]">You&apos;re sending</p>
                <p className="mt-1.5 text-2xl font-medium tabular tracking-tight">0</p>
                <p className="mt-1.5 text-xs text-[var(--color-text-muted)]">Balance · 1000 ST</p>
              </div>
              <div className="rounded-[12px] bg-[var(--color-surface-muted)] px-3.5 py-3 text-left">
                <p className="text-sm font-medium text-[var(--color-accent)]">Recipient</p>
                <p className="mt-1.5 text-sm text-[var(--color-text-muted)]">
                  Search by name or account
                </p>
              </div>
              <div className="btn-primary w-full !min-h-10 pointer-events-none select-none" aria-hidden>
                Continue
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/** Centers of the corner and edge handles, on the selection boundary. */
const HANDLES = [
  ["0%", "0%"],
  ["50%", "0%"],
  ["100%", "0%"],
  ["0%", "50%"],
  ["100%", "50%"],
  ["0%", "100%"],
  ["50%", "100%"],
  ["100%", "100%"],
] as const;

/** Design-tool selection chrome. Out of flow, so the heading box does not move. */
function HeadingSelection() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute -inset-6 outline outline-1 outline-[var(--color-accent)]"
    >
      <span className="absolute bottom-full left-0 mb-2 text-[11px] font-medium leading-none tracking-tight text-[var(--color-accent)]">
        Heading
      </span>
      {HANDLES.map(([x, y]) => (
        <span
          key={`${x}-${y}`}
          className="absolute size-[7px] -translate-x-1/2 -translate-y-1/2 border border-[var(--color-accent)] bg-white"
          style={{ left: x, top: y }}
        />
      ))}
    </div>
  );
}
