import { useRef, useState, type MouseEvent, type PointerEvent } from "react";
import { Link } from "react-router-dom";
import { play } from "cuelume";
import { SentinelMark } from "./SentinelMark";

const SPRING = "cubic-bezier(0.34, 1.56, 0.64, 1)";

/** Text size + gap; mark is always 1.15em so it tracks cap height (better-ui). */
const SIZE = {
  sm: { text: "text-[1.0625rem]", gap: "gap-2" }, // 17px / 8px — navbar density
  md: { text: "text-xl", gap: "gap-2.5" }, // 20px / 10px
  lg: { text: "text-2xl", gap: "gap-3" }, // 24px / 12px
} as const;

export function BrandMark({
  size = "md",
  inverse = false,
}: {
  size?: "sm" | "md" | "lg";
  inverse?: boolean;
}) {
  const { text, gap } = SIZE[size];
  const [turns, setTurns] = useState(0);
  const reducedMotion = useRef(
    typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );

  const onMarkEnter = () => {
    if (reducedMotion.current) return;
    setTurns((n) => n + 1);
  };

  const onMarkClick = (event: MouseEvent<HTMLSpanElement>) => {
    event.preventDefault();
    event.stopPropagation();
    try {
      play("chime", { volume: 0.4 });
    } catch {
      // Web Audio may be blocked
    }
  };

  const onMarkPointerDown = (event: PointerEvent<HTMLSpanElement>) => {
    if (event.pointerType === "mouse") event.preventDefault();
  };

  return (
    <Link
      to="/"
      aria-label="Sentinel home"
      className={`inline-flex items-center ${gap} no-underline tracking-[-0.028em] ${
        inverse ? "text-white" : "text-[var(--color-text)]"
      }`}
    >
      <span
        className="brand-mark-dot relative inline-grid size-[1.15em] shrink-0 place-items-center"
        aria-hidden
        onPointerEnter={onMarkEnter}
        onClick={onMarkClick}
        onPointerDown={onMarkPointerDown}
      >
        <SentinelMark
          className="block size-full"
          style={{
            ["--turn" as string]: `${turns * 120}deg`,
            transform: "rotate(var(--turn, 0deg))",
            transition: reducedMotion.current
              ? undefined
              : `transform 0.72s ${SPRING}`,
          }}
        />
      </span>
      <span className={`font-semibold leading-none lowercase ${text}`}>sentinel</span>
    </Link>
  );
}
