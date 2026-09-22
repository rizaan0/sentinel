import type { ReactNode, SVGProps } from "react";

export type IconWeight = "regular" | "semibold";
export type IconVariant = "outline" | "fill";

export type IconProps = SVGProps<SVGSVGElement> & {
  /** Optical stroke: regular (1.5) beside 400 text; semibold (2) beside 500–600. */
  weight?: IconWeight;
  /** Outline = default; fill = active/selected. */
  variant?: IconVariant;
  /** Accessible name. Omit for decorative icons (aria-hidden). */
  title?: string;
  size?: number | string;
};

const STROKE: Record<IconWeight, number> = {
  regular: 1.5,
  semibold: 2,
};

/**
 * SF Symbols–style base: 24pt grid, round caps/joins, currentColor.
 * Paths approximate Apple SF Symbol silhouettes for cross-platform web use.
 */
export function IconBase({
  weight = "regular",
  title,
  size = 24,
  className = "",
  children,
  ...rest
}: IconProps & { children: ReactNode }) {
  const labelled = Boolean(title);
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={STROKE[weight]}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`shrink-0 ${className}`}
      aria-hidden={labelled ? undefined : true}
      role={labelled ? "img" : undefined}
      {...rest}
    >
      {title ? <title>{title}</title> : null}
      {children}
    </svg>
  );
}

type SymbolProps = IconProps;

function HouseOutline(props: SymbolProps) {
  return (
    <IconBase {...props}>
      <path d="M4.5 10.5 12 4l7.5 6.5V19a1.5 1.5 0 0 1-1.5 1.5h-3.75v-5.25h-4.5V20.5H6A1.5 1.5 0 0 1 4.5 19z" />
    </IconBase>
  );
}

function HouseFill(props: SymbolProps) {
  return (
    <IconBase {...props} stroke="none" fill="currentColor">
      <path d="M11.35 3.35a1 1 0 0 1 1.3 0l7.5 6.5a1 1 0 0 1 .35.76V19a2.5 2.5 0 0 1-2.5 2.5h-3.25a1 1 0 0 1-1-1v-5.25h-3.5V20.5a1 1 0 0 1-1 1H6A2.5 2.5 0 0 1 3.5 19v-8.39a1 1 0 0 1 .35-.76z" />
    </IconBase>
  );
}

function PaperplaneOutline(props: SymbolProps) {
  return (
    <IconBase {...props}>
      <path d="m21 3-8.5 18-2.2-7.3L3 11.5z" />
      <path d="M21 3 10.3 13.7" />
    </IconBase>
  );
}

function PaperplaneFill(props: SymbolProps) {
  return (
    <IconBase {...props} stroke="none" fill="currentColor">
      <path d="M20.7 2.3a1 1 0 0 1 1.05.18 1 1 0 0 1 .25 1.05L13.2 21.4a1.1 1.1 0 0 1-2.05.05l-2.15-7.15L1.9 12.2a1.1 1.1 0 0 1 .05-2.05L20.7 2.3Z" />
    </IconBase>
  );
}

function ListBulletOutline(props: SymbolProps) {
  return (
    <IconBase {...props}>
      <path d="M9 7h11M9 12h11M9 17h11" />
      <circle cx="5" cy="7" r="1" fill="currentColor" stroke="none" />
      <circle cx="5" cy="12" r="1" fill="currentColor" stroke="none" />
      <circle cx="5" cy="17" r="1" fill="currentColor" stroke="none" />
    </IconBase>
  );
}

function ListBulletFill(props: SymbolProps) {
  return (
    <IconBase {...props} stroke="none" fill="currentColor">
      <rect x="8" y="5.5" width="12.5" height="3" rx="1.2" />
      <rect x="8" y="10.5" width="12.5" height="3" rx="1.2" />
      <rect x="8" y="15.5" width="12.5" height="3" rx="1.2" />
      <circle cx="5" cy="7" r="1.35" />
      <circle cx="5" cy="12" r="1.35" />
      <circle cx="5" cy="17" r="1.35" />
    </IconBase>
  );
}

function PersonCircleOutline(props: SymbolProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="10" r="3" />
      <path d="M6.8 18.2a6.2 6.2 0 0 1 10.4 0" />
    </IconBase>
  );
}

function PersonCircleFill(props: SymbolProps) {
  return (
    <IconBase {...props} stroke="none" fill="currentColor">
      <path
        fillRule="evenodd"
        d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm0 4.5a3.25 3.25 0 1 1 0 6.5 3.25 3.25 0 0 1 0-6.5ZM7.2 17.6A6.4 6.4 0 0 1 12 15.5c1.9 0 3.6.83 4.8 2.1A8.45 8.45 0 0 1 12 20.5a8.45 8.45 0 0 1-4.8-2.9Z"
        clipRule="evenodd"
      />
    </IconBase>
  );
}

function Xmark(props: SymbolProps) {
  return (
    <IconBase {...props}>
      <path d="M6 6l12 12M18 6 6 18" />
    </IconBase>
  );
}

function Checkmark(props: SymbolProps) {
  return (
    <IconBase {...props}>
      <path d="m5 12.5 4.5 4.5L19 7" />
    </IconBase>
  );
}

function DocOnDoc(props: SymbolProps) {
  return (
    <IconBase {...props}>
      <path d="M9 8.5A1.5 1.5 0 0 1 10.5 7H17a2 2 0 0 1 2 2v9.5A1.5 1.5 0 0 1 17.5 20H11a2 2 0 0 1-2-2z" />
      <path d="M7 16.5V6a2 2 0 0 1 2-2h7.5" />
    </IconBase>
  );
}

function ChevronLeft(props: SymbolProps) {
  return (
    <IconBase {...props} className={`icon-directional ${props.className ?? ""}`}>
      <path d="m14.5 5-6 7 6 7" />
    </IconBase>
  );
}

function ChevronRight(props: SymbolProps) {
  return (
    <IconBase {...props} className={`icon-directional ${props.className ?? ""}`}>
      <path d="m9.5 5 6 7-6 7" />
    </IconBase>
  );
}

function Magnifyingglass(props: SymbolProps) {
  return (
    <IconBase {...props}>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4 4" />
    </IconBase>
  );
}

function Lock(props: SymbolProps) {
  return (
    <IconBase {...props}>
      <rect x="5.5" y="10.5" width="13" height="10" rx="2" />
      <path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5" />
    </IconBase>
  );
}

function ArrowUpRight(props: SymbolProps) {
  return (
    <IconBase {...props} className={`icon-directional ${props.className ?? ""}`}>
      <path d="M7 17 17 7M9 7h8v8" />
    </IconBase>
  );
}

function Tray(props: SymbolProps) {
  return (
    <IconBase {...props}>
      <path d="M4 14.5 6.2 6.8A2 2 0 0 1 8.1 5.5h7.8a2 2 0 0 1 1.9 1.3L20 14.5" />
      <path d="M4 14.5h4.2l1.3 2h5l1.3-2H20v3a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z" />
    </IconBase>
  );
}

function ExclamationmarkCircle(props: SymbolProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v5" />
      <circle cx="12" cy="16.5" r="0.8" fill="currentColor" stroke="none" />
    </IconBase>
  );
}

function ArrowRight(props: SymbolProps) {
  return (
    <IconBase {...props} className={`icon-directional ${props.className ?? ""}`}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </IconBase>
  );
}

function RectangleStack(props: SymbolProps) {
  return (
    <IconBase {...props}>
      <path d="M7 8.5h11.5A1.5 1.5 0 0 1 20 10v8.5A1.5 1.5 0 0 1 18.5 20H7a1.5 1.5 0 0 1-1.5-1.5V10A1.5 1.5 0 0 1 7 8.5Z" />
      <path d="M5.5 6.5h11" />
      <path d="M7.5 4h9" />
    </IconBase>
  );
}

/** SF Symbol–style names used across Sentinel. */
export const SfSymbols = {
  house: { outline: HouseOutline, fill: HouseFill },
  paperplane: { outline: PaperplaneOutline, fill: PaperplaneFill },
  "list.bullet": { outline: ListBulletOutline, fill: ListBulletFill },
  "person.crop.circle": { outline: PersonCircleOutline, fill: PersonCircleFill },
  xmark: { outline: Xmark, fill: Xmark },
  checkmark: { outline: Checkmark, fill: Checkmark },
  "doc.on.doc": { outline: DocOnDoc, fill: DocOnDoc },
  "chevron.left": { outline: ChevronLeft, fill: ChevronLeft },
  "chevron.right": { outline: ChevronRight, fill: ChevronRight },
  magnifyingglass: { outline: Magnifyingglass, fill: Magnifyingglass },
  lock: { outline: Lock, fill: Lock },
  "arrow.up.right": { outline: ArrowUpRight, fill: ArrowUpRight },
  "arrow.right": { outline: ArrowRight, fill: ArrowRight },
  tray: { outline: Tray, fill: Tray },
  "exclamationmark.circle": { outline: ExclamationmarkCircle, fill: ExclamationmarkCircle },
  "rectangle.stack": { outline: RectangleStack, fill: RectangleStack },
} as const;

export type SfSymbolName = keyof typeof SfSymbols;

export function SfIcon({
  name,
  variant = "outline",
  ...props
}: IconProps & { name: SfSymbolName }) {
  const entry = SfSymbols[name];
  const Glyph = variant === "fill" ? entry.fill : entry.outline;
  return <Glyph variant={variant} {...props} />;
}

/**
 * Outline ↔ fill cross-fade for selected chrome (nav tabs).
 * Both glyphs stay mounted so enter/exit animate together.
 */
export function SfIconSwap({
  name,
  active,
  weight = "semibold",
  size = 22,
  className = "",
}: {
  name: SfSymbolName;
  active: boolean;
  weight?: IconWeight;
  size?: number;
  className?: string;
}) {
  const Outline = SfSymbols[name].outline;
  const Fill = SfSymbols[name].fill;
  return (
    <span className={`relative inline-flex size-[1.375rem] items-center justify-center ${className}`}>
      <span
        className={`absolute inset-0 flex items-center justify-center transition-[opacity,filter,scale] duration-300 ease-[cubic-bezier(0.2,0,0,1)] ${
          active ? "scale-100 opacity-100 blur-0" : "scale-[0.25] opacity-0 blur-[4px]"
        }`}
      >
        <Fill weight={weight} size={size} variant="fill" />
      </span>
      <span
        className={`flex items-center justify-center transition-[opacity,filter,scale] duration-300 ease-[cubic-bezier(0.2,0,0,1)] ${
          active ? "scale-[0.25] opacity-0 blur-[4px]" : "scale-100 opacity-100 blur-0"
        }`}
      >
        <Outline weight={weight} size={size} variant="outline" />
      </span>
    </span>
  );
}
