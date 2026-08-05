import { Link } from "react-router-dom";
import Reveal from "../components/Reveal";

export default function HeroSection() {
  return (
    <section className="max-w-6xl mx-auto px-6 pt-20 pb-24 text-center">
      <Reveal>
        <span className="inline-block text-xs font-medium tracking-wide uppercase text-neutral-500 border border-neutral-300 dark:border-neutral-700 rounded-full px-3 py-1">
          Real-time transaction monitoring platform
        </span>
      </Reveal>

      <Reveal delayMs={100}>
        <h1 className="mt-6 text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight">
          A payment app on the surface.
          <br />
          <span className="text-neutral-500">An intelligence platform underneath.</span>
        </h1>
      </Reveal>

      <Reveal delayMs={200}>
        <p className="mt-6 max-w-2xl mx-auto text-lg text-neutral-600 dark:text-neutral-400">
          Sentinel looks and feels like GPay or PhonePe - send money instantly with ST Coins.
          But every transaction is silently evaluated by a real-time monitoring engine that
          validates the ledger, detects fraud from behavior, predicts future risk, and explains
          itself with an AI investigation assistant.
        </p>
      </Reveal>

      <Reveal delayMs={300}>
        <div className="mt-10 flex items-center justify-center gap-4">
          <Link to="/signup" className="btn-primary px-6 py-3 text-base">
            Create your account
          </Link>
          <Link
            to="/login"
            className="px-6 py-3 text-base rounded-md border border-neutral-300 dark:border-neutral-700"
          >
            Log in
          </Link>
        </div>
      </Reveal>

      <Reveal delayMs={400}>
        <p className="mt-4 text-sm text-neutral-400">
          Every new account starts with 1000 ST Coins - no real banking information required.
        </p>
      </Reveal>
    </section>
  );
}
