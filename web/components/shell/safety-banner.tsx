import { BANNER_DISCLAIMER } from "@/lib/safety";

/** Persistent, page-level reminder of the cure boundary (spec §7). Always rendered. */
export function SafetyBanner() {
  return (
    <div className="flex items-start gap-2.5 border-b border-warn/25 bg-warn/[0.07] px-5 py-2 text-xs text-warn/90 sm:px-8">
      <svg
        viewBox="0 0 24 24"
        className="mt-0.5 h-3.5 w-3.5 flex-none"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden
      >
        <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
      <p className="leading-relaxed">{BANNER_DISCLAIMER}</p>
    </div>
  );
}
