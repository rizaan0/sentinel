import { Link } from "react-router-dom";
import Reveal from "../components/Reveal";

export default function CtaSection() {
  return (
    <section className="max-w-4xl mx-auto px-6 py-24 text-center">
      <Reveal>
        <h2 className="text-3xl font-bold">See it for yourself</h2>
        <p className="mt-3 text-neutral-500">
          Sign up, send a few transfers, then try to trigger a fraud alert - repeat transfers,
          a big outlier, or a fast circular chain of payments.
        </p>
        <div className="mt-8">
          <Link to="/signup" className="btn-primary px-6 py-3 text-base">
            Get started with 1000 ST Coins
          </Link>
        </div>
      </Reveal>
    </section>
  );
}
