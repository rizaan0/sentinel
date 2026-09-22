const PALETTE = [
  "bg-signal-100 text-signal-800",
  "bg-ink-100 text-ink-700",
  "bg-signal-50 text-signal-900",
  "bg-ink-50 text-ink-800",
];

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function colorFor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash + name.charCodeAt(i) * (i + 1)) % 997;
  return PALETTE[hash % PALETTE.length];
}

type Props = {
  name: string;
  size?: "sm" | "md" | "lg";
};

const SIZE = {
  sm: "h-9 w-9 text-xs",
  md: "h-11 w-11 text-sm",
  lg: "h-14 w-14 text-base",
};

export function Avatar({ name, size = "md" }: Props) {
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-full font-bold ${SIZE[size]} ${colorFor(name)}`}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}
