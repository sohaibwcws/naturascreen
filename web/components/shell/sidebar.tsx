"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV: { href: string; label: string; icon: React.ReactNode }[] = [
  { href: "/", label: "Dashboard", icon: <IconGrid /> },
  { href: "/compounds", label: "Compounds", icon: <IconFlask /> },
  { href: "/targets", label: "Targets", icon: <IconTarget /> },
  { href: "/neoantigens", label: "Neoantigens", icon: <IconShield /> },
  { href: "/experiments", label: "Experiments", icon: <IconBeaker /> },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sticky top-0 hidden h-screen w-60 flex-none flex-col border-r border-base-700 bg-base-850/80 backdrop-blur md:flex">
      <Link href="/" className="flex items-center gap-2.5 px-5 py-5">
        <span className="grid h-8 w-8 place-items-center rounded-md bg-accent/15 text-accent">
          <IconHelix />
        </span>
        <span className="text-sm font-semibold tracking-tight text-ink">
          Natura<span className="text-accent">Screen</span>
        </span>
      </Link>

      <nav className="flex flex-col gap-0.5 px-3">
        {NAV.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition",
                active
                  ? "bg-accent/10 text-accent"
                  : "text-ink-muted hover:bg-base-800 hover:text-ink",
              )}
            >
              <span className={cn("h-4 w-4", active ? "text-accent" : "text-ink-faint")}>
                {item.icon}
              </span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto px-5 py-5 text-[11px] leading-relaxed text-ink-faint">
        Open-source natural-compound screening. Outputs are research hypotheses, never
        treatments.
      </div>
    </aside>
  );
}

/* --- inline icons (no icon dependency) --- */

function svg(children: React.ReactNode) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-full w-full"
    >
      {children}
    </svg>
  );
}

function IconGrid() {
  return svg(
    <>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </>,
  );
}

function IconFlask() {
  return svg(
    <>
      <path d="M9 3h6M10 3v6L5 19a1.5 1.5 0 0 0 1.4 2h11.2A1.5 1.5 0 0 0 19 19l-5-10V3" />
      <path d="M7.5 15h9" />
    </>,
  );
}

function IconTarget() {
  return svg(
    <>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="12" cy="12" r="0.6" fill="currentColor" />
    </>,
  );
}

function IconShield() {
  return svg(<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3Z" />);
}

function IconBeaker() {
  return svg(
    <>
      <path d="M8 3h8M9 3v5l-4.5 8A2 2 0 0 0 6.3 19h11.4a2 2 0 0 0 1.8-3L15 8V3" />
      <circle cx="12" cy="15" r="1" fill="currentColor" />
    </>,
  );
}

function IconHelix() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4">
      <path d="M7 3c0 4 10 6 10 9s-10 5-10 9M17 3c0 4-10 6-10 9s10 5 10 9" strokeLinecap="round" />
    </svg>
  );
}
