import { ShaderBackground } from "@/components/motion/shader-background";
import { cn } from "@/lib/utils";

/** Grain — Pastel. Fills its positioned parent and does not take layout space. */
export function GrainPastelBackground({ className }: { className?: string }) {
  return (
    <ShaderBackground
      variant="grain-gradient"
      colors={["#ffd6e8", "#c9e4ff", "#fff3c4", "#d9c9ff"]}
      colorBack="#ffffff"
      softness={0.85}
      speed={0.3}
      className={cn("pointer-events-none absolute inset-0 h-full w-full", className)}
    />
  );
}
