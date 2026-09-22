type Props = {
  value: string | number;
  signed?: boolean;
  direction?: "sent" | "received" | "neutral";
  size?: "sm" | "md" | "lg" | "xl";
  suffix?: string;
};

const SIZE = {
  sm: "text-sm",
  md: "text-base",
  lg: "text-2xl",
  xl: "text-4xl tracking-tight",
};

export function Amount({
  value,
  signed = false,
  direction = "neutral",
  size = "md",
  suffix = "ST",
}: Props) {
  const prefix =
    signed && direction === "sent" ? "−" : signed && direction === "received" ? "+" : "";
  const color =
    direction === "sent"
      ? "text-[var(--color-rose-600)]"
      : direction === "received"
        ? "text-[var(--color-accent)]"
        : "text-[var(--color-text)]";

  return (
    <span className={`tabular font-bold ${SIZE[size]} ${color}`}>
      {prefix}
      {value} {suffix}
    </span>
  );
}
