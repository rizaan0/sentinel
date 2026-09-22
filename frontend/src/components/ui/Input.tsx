import type { InputHTMLAttributes } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  invalid?: boolean;
};

export function Input({ invalid, className = "", id, ...rest }: Props) {
  return (
    <input
      id={id}
      className={`input ${invalid ? "border-[var(--color-danger)] focus:ring-[var(--color-danger)]" : ""} ${className}`}
      aria-invalid={invalid || undefined}
      {...rest}
    />
  );
}
