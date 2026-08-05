import Reveal from "../components/Reveal";

const FEATURES = [
  {
    title: "Instant payments",
    description:
      "Search a recipient by account number, review the transfer, and authorize it with your Transaction PIN - a familiar, GPay/PhonePe-style flow with instant receipts.",
  },
  {
    title: "Transaction Monitoring Engine",
    description:
      "Every transfer is validated, ledgered with double-entry accounting, and reconciled - independently of fraud analysis - so the books are always provably correct.",
  },
  {
    title: "Behavioral fraud detection",
    description:
      "Rapid repeated transfers, circular fund flow, unusually large transfers, and bursts of small transactions are recognized as patterns, not manually labeled.",
  },
  {
    title: "ML anomaly detection",
    description:
      "An Isolation Forest model trained on transaction behavior adds a statistical anomaly score alongside the rule engine's findings.",
  },
  {
    title: "Predictive analytics",
    description:
      "Users whose fraud-alert frequency and severity are trending upward are ranked and surfaced before they escalate further.",
  },
  {
    title: "AI Investigation Assistant",
    description:
      "Ask a local LLM why a transaction was flagged or to summarize an account's recent behavior - it explains monitoring results, it never decides fraud.",
  },
];

export default function FeaturesSection() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-20">
      <Reveal>
        <h2 className="text-3xl font-bold text-center">
          One platform, two very different experiences
        </h2>
        <p className="mt-3 text-center text-neutral-500 max-w-2xl mx-auto">
          Users see a simple wallet. Administrators see a full operational intelligence
          platform built on the same data.
        </p>
      </Reveal>

      <div className="mt-14 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {FEATURES.map((feature, index) => (
          <Reveal key={feature.title} delayMs={index * 80}>
            <div className="h-full rounded-xl border border-neutral-200 dark:border-neutral-800 p-6">
              <h3 className="font-semibold">{feature.title}</h3>
              <p className="mt-2 text-sm text-neutral-500">{feature.description}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
