import { HelpCircle, ShieldCheck, Wallet } from "lucide-react";
import { BouncyAccordion } from "@/components/motion/bouncy-accordion";
import { LANDING_FRAME, LANDING_PAD } from "../landingRail";

const items = [
  {
    id: "what",
    title: "What is Sentinel?",
    description:
      "Sentinel sends ST Coins like a wallet and scores every transfer for fraud in real time.",
    icon: <HelpCircle className="h-4 w-4" />,
  },
  {
    id: "coins",
    title: "What is an ST Coin?",
    description:
      "ST Coins are the balance you send and receive. A new account starts with 1000 ST.",
    icon: <Wallet className="h-4 w-4" />,
  },
  {
    id: "risk",
    title: "What if a transfer looks unusual?",
    description:
      "Unusual is not the same as fraudulent. Some transfers ask you to confirm. A higher risk can hold only the flagged amount.",
    icon: <ShieldCheck className="h-4 w-4" />,
  },
];

export default function FaqSection() {
  return (
    <section id="faq" className={`${LANDING_PAD} scroll-mt-32 pb-16`}>
      <div className={LANDING_FRAME}>
        <h2 className="text-sm font-medium text-[var(--color-text)]">FAQ</h2>
        <div className="mt-4 w-full max-w-sm">
          <BouncyAccordion items={items} />
        </div>
      </div>
    </section>
  );
}
