import type { SVGProps } from "react";

/**
 * Brand mark — trefoil with center aperture (Cuelume-style solid mark).
 * Monochrome via currentColor; evenodd cutout keeps the hole crisp at all sizes.
 */
export function SentinelMark({
  className = "",
  title,
  ...rest
}: SVGProps<SVGSVGElement> & { title?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      fill="currentColor"
      className={`block shrink-0 ${className}`}
      aria-hidden={title ? undefined : true}
      role={title ? "img" : undefined}
      {...rest}
    >
      {title ? <title>{title}</title> : null}
      <path
        fillRule="evenodd"
        d="M17.10 19.27A15 15 0 0 1 46.90 19.27A9 9 0 0 0 50.48 25.46A15 15 0 0 1 35.57 51.26A9 9 0 0 0 28.42 51.27A15 15 0 0 1 13.53 25.46A9 9 0 0 0 17.10 19.27ZM32 24.5A7.5 7.5 0 1 0 32 39.5A7.5 7.5 0 1 0 32 24.5Z"
      />
    </svg>
  );
}
