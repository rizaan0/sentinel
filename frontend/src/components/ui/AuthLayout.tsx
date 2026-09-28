import type { ReactNode } from "react";
import { BrandMark } from "./BrandMark";

type Props = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  /** Login and signup paint the pastel grain shader. Other auth pages keep the default canvas. */
  transparent?: boolean;
};

export function AuthLayout({ title, subtitle, children, transparent = false }: Props) {
  return (
    <main
      className={`${transparent ? "bg-transparent" : "app-atmosphere"} relative flex min-h-dvh w-full items-center justify-center overflow-hidden px-4 py-10 sm:px-6`}
    >
      <div className="relative w-full max-w-md sm:max-w-lg">
        <div className="mb-8">
          <BrandMark />
          <h1 className="mt-8 text-2xl font-bold tracking-tight text-balance text-[var(--color-text)] sm:text-3xl">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-2 text-sm leading-relaxed text-[var(--color-text-muted)] text-pretty sm:text-base">
              {subtitle}
            </p>
          )}
        </div>
        <div className="surface-card p-5 shadow-[var(--shadow-md)] sm:p-7">{children}</div>
      </div>
    </main>
  );
}
