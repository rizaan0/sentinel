import { useEffect, useState } from "react";
import { Helmet } from "react-helmet-async";
import { GrainPastelBackground } from "@/components/motion/grain-pastel-background";
import { LiquidNavbarDemo } from "@/components/motion/liquid-glass";
import HeroSection from "./sections/HeroSection";
import FaqSection from "./sections/FaqSection";
import TermsSection from "./sections/TermsSection";
import Footer from "./sections/Footer";

export default function LandingPage() {
  const [hash, setHash] = useState(() => window.location.hash);

  useEffect(() => {
    const root = document.documentElement;
    const previousScroll = root.style.scrollBehavior;
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      root.style.scrollBehavior = "smooth";
    }
    const onHash = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHash);
    return () => {
      root.style.scrollBehavior = previousScroll;
      window.removeEventListener("hashchange", onHash);
    };
  }, []);

  return (
    <div className="relative flex h-dvh w-full flex-col overflow-hidden bg-white text-[var(--color-text)]">
      <GrainPastelBackground className="fixed inset-0 h-auto w-auto opacity-[0.999]" />
      <Helmet>
        <title>Sentinel — Real-Time Transaction Monitoring</title>
        <meta
          name="description"
          content="Send ST Coins instantly while every transfer is monitored for fraud in real time."
        />
        <meta property="og:title" content="Sentinel — Real-Time Transaction Monitoring" />
        <meta
          property="og:description"
          content="Instant payments with real-time fraud monitoring."
        />
        <meta property="og:type" content="website" />
      </Helmet>

      <LiquidNavbarDemo />
      <main className="flex min-h-0 flex-1 flex-col overflow-hidden pt-28 sm:pt-32">
        {hash === "#faq" ? <FaqSection /> : hash === "#terms" ? <TermsSection /> : <HeroSection />}
      </main>
      <Footer />
    </div>
  );
}
