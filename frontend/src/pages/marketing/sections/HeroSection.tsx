import { Link } from "react-router-dom";
import Reveal from "../components/Reveal";

export default function HeroSection() {
  return (
    <section className="app-atmosphere relative flex flex-1 flex-col overflow-hidden">
      <div className="relative mx-auto flex w-full max-w-5xl flex-1 flex-col items-center justify-center px-5 py-8 text-center sm:px-6 sm:py-10">
        <div className="flex w-full max-w-3xl flex-col items-center">
          <Reveal>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-[var(--color-accent)]">
              sentinel
            </p>
          </Reveal>

          <Reveal delayMs={80}>
            <h1 className="mt-3 max-w-3xl text-[1.85rem] font-extrabold leading-[1.12] tracking-tight text-balance text-[var(--color-text)] sm:mt-4 sm:text-5xl md:text-[3.25rem] md:leading-[1.1]">
              Payments that feel instant. Monitoring that never sleeps.
            </h1>
          </Reveal>

          <Reveal delayMs={160}>
            <p className="mt-4 max-w-xl text-[0.95rem] leading-relaxed text-pretty text-[var(--color-text-muted)] sm:mt-5 sm:text-lg">
              Send ST Coins like a modern wallet — while every transfer is ledgered,
              reconciled, and scored for fraud in real time.
            </p>
          </Reveal>

          <Reveal delayMs={240}>
            <div className="mt-7 flex flex-wrap items-center justify-center gap-3 sm:mt-8">
              <Link to="/signup" className="btn-primary px-7 text-base">
                Get Started
              </Link>
              <Link to="/login" className="btn-secondary px-7 text-base">
                Log in
              </Link>
            </div>
          </Reveal>
        </div>

        <Reveal delayMs={320}>
          <div className="mt-8 w-full max-w-md sm:mt-10">
            <div className="surface-card p-2 shadow-[var(--shadow-md)]">
              <div className="flex gap-1 rounded-[var(--radius-pill)] bg-[var(--color-surface-muted)] p-1 text-xs font-semibold">
                <span className="flex-1 rounded-[var(--radius-pill)] bg-white px-3 py-2 text-[var(--color-accent)] shadow-[var(--shadow-sm)]">
                  Send
                </span>
                <span className="flex-1 px-3 py-2 text-[var(--color-text-muted)]">Activity</span>
                <span className="flex-1 px-3 py-2 text-[var(--color-text-muted)]">Profile</span>
              </div>
              <div className="mt-2 space-y-2 p-3">
                <div className="surface-inset p-4 text-left">
                  <p className="label-accent">You&apos;re sending</p>
                  <p className="mt-2 text-3xl font-extrabold tabular">0</p>
                  <p className="mt-3 text-xs text-[var(--color-text-muted)]">Balance · 1000 ST</p>
                </div>
                <div className="surface-inset p-4 text-left">
                  <p className="label-accent">Recipient</p>
                  <p className="mt-2 text-sm font-semibold text-[var(--color-text-muted)]">
                    Search by name or account
                  </p>
                </div>
                <button type="button" className="btn-primary w-full" tabIndex={-1}>
                  Continue
                </button>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
