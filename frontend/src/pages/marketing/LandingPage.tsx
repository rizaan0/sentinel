import { Helmet } from "react-helmet-async";
import Navbar from "./sections/Navbar";
import HeroSection from "./sections/HeroSection";
import FeaturesSection from "./sections/FeaturesSection";
import ArchitectureSection from "./sections/ArchitectureSection";
import CtaSection from "./sections/CtaSection";
import Footer from "./sections/Footer";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100">
      <Helmet>
        <title>Sentinel - Real-Time Transaction Monitoring Platform</title>
        <meta
          name="description"
          content="Sentinel is a real-time transaction monitoring platform: instant peer-to-peer payments backed by a behavioral fraud detection engine, ML anomaly scoring, predictive analytics, and an AI investigation assistant."
        />
        <meta property="og:title" content="Sentinel - Real-Time Transaction Monitoring Platform" />
        <meta
          property="og:description"
          content="A payment app on the surface. An intelligence platform underneath."
        />
        <meta property="og:type" content="website" />
      </Helmet>

      <Navbar />
      <main>
        <HeroSection />
        <FeaturesSection />
        <ArchitectureSection />
        <CtaSection />
      </main>
      <Footer />
    </div>
  );
}
