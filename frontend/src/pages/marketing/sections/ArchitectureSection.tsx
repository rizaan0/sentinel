import Reveal from "../components/Reveal";

const STEPS = [
  {
    title: "You send money",
    description: "Transaction Service validates the recipient, amount, and Transaction PIN.",
  },
  {
    title: "Ledger Service records it",
    description:
      "Double-entry ledger entries are written and reconciled independently of fraud analysis.",
  },
  {
    title: "Transaction Completed Event fires",
    description:
      "Only after PostgreSQL confirms the commit - fanning out to the Monitoring Engine and the live admin feed in parallel.",
  },
  {
    title: "Rules, statistics, and ML evaluate it",
    description:
      "Three independent evaluators feed a combined Risk Score Engine. Most transactions pass through silently.",
  },
  {
    title: "Admins see it, live",
    description:
      "Fraud alerts and reconciliation reports appear instantly, explainable on demand by the AI Investigation Assistant.",
  },
];

export default function ArchitectureSection() {
  return (
    <section className="max-w-4xl mx-auto px-6 py-20">
      <Reveal>
        <h2 className="text-3xl font-bold text-center">What happens behind the scenes</h2>
        <p className="mt-3 text-center text-neutral-500">
          The payment interface generates authentic transaction behavior. The monitoring
          platform turns that behavior into operational intelligence.
        </p>
      </Reveal>

      <ol className="mt-14 space-y-8">
        {STEPS.map((step, index) => (
          <Reveal key={step.title} delayMs={index * 100}>
            <li className="flex gap-4">
              <span className="flex-shrink-0 w-8 h-8 rounded-full bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 flex items-center justify-center text-sm font-semibold">
                {index + 1}
              </span>
              <div>
                <p className="font-semibold">{step.title}</p>
                <p className="text-sm text-neutral-500">{step.description}</p>
              </div>
            </li>
          </Reveal>
        ))}
      </ol>
    </section>
  );
}
