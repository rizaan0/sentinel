import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";

const VARIANT_CLASS: Record<Variant, string> = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  ghost: "btn-ghost",
};

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  children: ReactNode;
  fullWidth?: boolean;
};

export function Button({
  variant = "primary",
  fullWidth,
  className = "",
  children,
  type = "button",
  ...rest
}: Props) {
  const cueAttrs =
    variant === "primary"
      ? { "data-cuelume-press": "pulse", "data-cuelume-release": "" }
      : variant === "secondary"
        ? { "data-cuelume-press": "", "data-cuelume-release": "" }
        : {};

  return (
    <button
      type={type}
      className={`${VARIANT_CLASS[variant]} ${fullWidth ? "w-full" : ""} ${className}`}
      {...cueAttrs}
      {...rest}
    >
      {children}
    </button>
  );
}
