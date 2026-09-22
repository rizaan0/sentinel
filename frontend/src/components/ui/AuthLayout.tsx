import type { ReactNode } from "react";
import { BrandMark } from "./BrandMark";

type Props = {
  title: string;
  subtitle?: string;
  children: ReactNode;
};

export function AuthLayout({ title, subtitle, children }: Props) {
  return (
    <main className="app-atmosphere relative min-h-dvh overflow-hidden">
      <div className="relative mx-auto flex min-h-dvh w-full max-w-md flex-col justify-center px-5 py-10">
        <div className="mb-8">
          <BrandMark />
          <h1 className="mt-8 text-2xl font-extrabold tracking-tight text-balance text-[var(--color-text)]">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-2 text-sm text-[var(--color-text-muted)] text-pretty">{subtitle}</p>
          )}
        </div>
        <div className="surface-card p-5 sm:p-6 shadow-[var(--shadow-md)]">{children}</div>
      </div>
    </main>
  );
}
