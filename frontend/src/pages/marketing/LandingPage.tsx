import { Helmet } from "react-helmet-async";
import Navbar from "./sections/Navbar";
import HeroSection from "./sections/HeroSection";
import Footer from "./sections/Footer";

export default function LandingPage() {
  return (
    <div className="flex min-h-dvh flex-col bg-white text-[var(--color-text)]">
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

      <Navbar />
      <main className="flex flex-1 flex-col">
        <HeroSection />
      </main>
      <Footer />
    </div>
  );
}
