import { Helmet } from "react-helmet-async";
import { GrainPastelBackground } from "@/components/motion/grain-pastel-background";
import { LiquidNavbarDemo } from "@/components/motion/liquid-glass";
import HeroSection from "./sections/HeroSection";
import Footer from "./sections/Footer";

export default function LandingPage() {
  return (
    <div className="relative flex min-h-dvh flex-col bg-white text-[var(--color-text)]">
      <GrainPastelBackground className="opacity-[0.999]" />
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
      <main className="flex min-h-0 flex-1 flex-col pt-28 sm:pt-32">
        <HeroSection />
      </main>
      <Footer />
    </div>
  );
}
