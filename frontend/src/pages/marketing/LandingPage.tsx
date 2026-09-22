import { Helmet } from "react-helmet-async";
import Navbar from "./sections/Navbar";
import HeroSection from "./sections/HeroSection";

export default function LandingPage() {
  return (
    <div className="flex min-h-dvh flex-col overflow-x-hidden bg-white text-[var(--color-text)]">
      <Helmet>
        <title>Sentinel — Real-Time Transaction Monitoring</title>
        <meta
          name="description"
          content="Sentinel is a real-time transaction monitoring platform: instant peer-to-peer payments backed by behavioral fraud detection, ML anomaly scoring, predictive analytics, and an AI investigation assistant."
        />
        <meta property="og:title" content="Sentinel — Real-Time Transaction Monitoring" />
        <meta
          property="og:description"
          content="A payment app on the surface. An intelligence platform underneath."
        />
        <meta property="og:type" content="website" />
      </Helmet>

      <Navbar />
      <main className="flex flex-1 flex-col">
        <HeroSection />
      </main>
    </div>
  );
}
