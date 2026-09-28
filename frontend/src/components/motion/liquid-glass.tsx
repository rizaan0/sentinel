import type { CSSProperties, ReactNode } from "react";
import { Link } from "react-router-dom";
import { BrandMark } from "@/components/ui/BrandMark";
import { SfIcon } from "@/components/ui/icons";
import { LANDING_FRAME, LANDING_PAD } from "@/pages/marketing/landingRail";

interface GlassEffectProps {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  href?: string;
  target?: string;
}

/**
 * Liquid Glass shell from the navbar reference.
 * The demo's link, cursor, and text styles stay off so the bar does not restyle its contents.
 */
export function GlassEffect({
  children,
  className = "",
  style = {},
  href,
  target = "_blank",
}: GlassEffectProps) {
  const glassStyle: CSSProperties = {
    boxShadow: "0 6px 6px rgba(0, 0, 0, 0.2), 0 0 20px rgba(0, 0, 0, 0.1)",
    transitionTimingFunction: "cubic-bezier(0.175, 0.885, 0.32, 2.2)",
    ...style,
  };

  const content = (
    <div
      className={
        "relative flex overflow-hidden transition-all duration-700 " +
        (href ? "cursor-pointer font-semibold text-black " : "") +
        className
      }
      style={glassStyle}
    >
      <div
        className="pointer-events-none absolute inset-0 z-0 overflow-hidden rounded-[inherit]"
        style={{
          backdropFilter: "blur(3px)",
          WebkitBackdropFilter: "blur(3px)",
          filter: "url(#glass-distortion)",
          isolation: "isolate",
        }}
      />
      <div
        className="pointer-events-none absolute inset-0 z-10 rounded-[inherit]"
        style={{ background: "rgba(255, 255, 255, 0.25)" }}
      />
      <div
        className="pointer-events-none absolute inset-0 z-20 overflow-hidden rounded-[inherit]"
        style={{
          boxShadow:
            "inset 2px 2px 1px 0 rgba(255, 255, 255, 0.5), inset -1px -1px 1px 1px rgba(255, 255, 255, 0.5)",
        }}
      />
      <div className="relative z-30 w-full">{children}</div>
    </div>
  );

  return href ? (
    <a href={href} target={target} rel="noopener noreferrer" className="block">
      {content}
    </a>
  ) : (
    content
  );
}

/**
 * Floating Liquid Glass navbar.
 * The shell uses the landing rail so it shares the footer’s edges and stays centered.
 * Width lives on the shell; the logo and actions keep their own size.
 * Hover still springs the shell (padding and radius) with the reference curve.
 */
export function LiquidNavbarDemo() {
  return (
    <header className={`pointer-events-none fixed inset-x-0 top-4 z-50 sm:top-5 ${LANDING_PAD}`}>
      <GlassFilter />
      <div className={LANDING_FRAME}>
        <GlassEffect className="pointer-events-auto w-full rounded-3xl p-3 hover:rounded-4xl hover:p-4">
          <nav className="flex h-14 w-full items-center justify-between sm:h-16">
          <BrandMark size="sm" />
          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              to="/login"
              className="inline-flex min-h-10 items-center px-3 text-sm font-medium tracking-tight text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text)]"
            >
              Log in
            </Link>
            <Link to="/signup" className="btn-primary !min-h-10 !px-4 !py-2 text-sm">
              Get Started
              <SfIcon name="arrow.right" weight="semibold" size={14} />
            </Link>
          </div>
          </nav>
        </GlassEffect>
      </div>
      <style>
        {`
        .hover\\:rounded-4xl:hover { border-radius: 4rem; }
      `}
      </style>
    </header>
  );
}

export function GlassFilter() {
  return (
    <svg aria-hidden style={{ position: "absolute", width: 0, height: 0 }}>
      <filter
        id="glass-distortion"
        x="0%"
        y="0%"
        width="100%"
        height="100%"
        filterUnits="objectBoundingBox"
      >
        <feTurbulence
          type="fractalNoise"
          baseFrequency="0.001 0.005"
          numOctaves="1"
          seed="17"
          result="turbulence"
        />
        <feComponentTransfer in="turbulence" result="mapped">
          <feFuncR type="gamma" amplitude="1" exponent="10" offset="0.5" />
          <feFuncG type="gamma" amplitude="0" exponent="1" offset="0" />
          <feFuncB type="gamma" amplitude="0" exponent="1" offset="0.5" />
        </feComponentTransfer>
        <feGaussianBlur in="turbulence" stdDeviation="3" result="softMap" />
        <feSpecularLighting
          in="softMap"
          surfaceScale="5"
          specularConstant="1"
          specularExponent="100"
          lightingColor="white"
          result="specLight"
        >
          <fePointLight x="-200" y="-200" z="300" />
        </feSpecularLighting>
        <feComposite
          in="specLight"
          operator="arithmetic"
          k1="0"
          k2="1"
          k3="1"
          k4="0"
          result="litImage"
        />
        <feDisplacementMap
          in="SourceGraphic"
          in2="softMap"
          scale="200"
          xChannelSelector="R"
          yChannelSelector="G"
        />
      </filter>
    </svg>
  );
}
