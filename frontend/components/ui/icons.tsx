import type { SVGProps } from "react";

export function MarkIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 40 40" fill="none" aria-hidden="true" {...props}>
      <rect width="40" height="40" rx="10" fill="currentColor" />
      <path d="M12 11h10l6 6v12H12V11Z" fill="white" fillOpacity=".18" />
      <path d="M22 11v7h6M16 22h8M16 26h6" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
