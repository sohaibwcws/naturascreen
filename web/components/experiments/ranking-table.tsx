"use client";

import { useState } from "react";
import type { ScoredCompound } from "@/lib/types";
import { cn, fmt } from "@/lib/utils";

interface ChannelBreakdown {
  available: boolean;
  raw: number | null;
  normalized: number | null;
  window: { raw_at_zero: number; raw_at_one: number; unit: string; note: string };
  weight_requested: number;
  weight_effective: number;
  contribution: number;
}

const CHANNELS = ["binding", "neoantigen", "response", "simulation"] as const;

export function RankingTable({ rows }: { rows: ScoredCompound[] }) {
  const [open, setOpen] = useState<number | null>(rows[0]?.compound_id ?? null);
  return (
    <div className="overflow-hidden rounded-lg border border-base-700">
      {rows.map((row) => {
        const isOpen = open === row.compound_id;
        return (
          <div key={row.compound_id} className="border-b border-base-750 last:border-0">
            <button
              className="flex w-full items-center gap-4 bg-base-800 px-4 py-3 text-left hover:bg-base-750"
              onClick={() => setOpen(isOpen ? null : row.compound_id)}
            >
              <span className="stat w-6 text-center text-sm text-ink-faint">{row.rank}</span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">{row.name}</span>
                <span className="font-mono text-[11px] text-ink-faint">{row.coconut_id}</span>
              </span>
              <span className="hidden gap-1.5 sm:flex">
                {CHANNELS.map((c) => (
                  <SubScoreChip key={c} label={c} value={row.normalized[c]} />
                ))}
              </span>
              <span className="w-28">
                <span className="stat text-sm text-accent">{fmt(row.combined_score, 3)}</span>
                <span className="mt-1 block h-1 rounded-full bg-base-700">
                  <span
                    className="block h-1 rounded-full bg-accent"
                    style={{ width: `${Math.round(row.combined_score * 100)}%` }}
                  />
                </span>
              </span>
            </button>

            {isOpen && (
              <div className="bg-base-850 px-4 py-3">
                {row.warnings.length > 0 && (
                  <ul className="mb-3 space-y-1">
                    {row.warnings.map((w, i) => (
                      <li key={i} className="text-xs text-warn">
                        ⚠ {w}
                      </li>
                    ))}
                  </ul>
                )}
                <table className="w-full text-xs">
                  <thead className="text-ink-faint">
                    <tr className="text-left">
                      <th className="py-1 font-medium">channel</th>
                      <th className="font-medium">raw</th>
                      <th className="font-medium">window (0 → 1)</th>
                      <th className="font-medium">normalized</th>
                      <th className="font-medium">weight</th>
                      <th className="font-medium">contribution</th>
                    </tr>
                  </thead>
                  <tbody>
                    {CHANNELS.map((c) => {
                      const b = row.breakdown[c] as ChannelBreakdown | undefined;
                      if (!b) return null;
                      return (
                        <tr key={c} className={cn("border-t border-base-750", !b.available && "opacity-50")}>
                          <td className="py-1 capitalize">{c}</td>
                          <td className="stat">{b.available ? fmt(b.raw, 2) : "unavailable"}</td>
                          <td className="stat text-ink-faint">
                            {b.window.raw_at_zero} → {b.window.raw_at_one}
                            <span className="ml-1 text-ink-faint">{b.window.unit}</span>
                          </td>
                          <td className="stat">{fmt(b.normalized, 3)}</td>
                          <td className="stat">{fmt(b.weight_effective, 2)}</td>
                          <td className="stat text-accent">{fmt(b.contribution, 3)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function SubScoreChip({ label, value }: { label: string; value: number | null }) {
  return (
    <span
      className="chip flex-col gap-0 px-2 py-0.5 text-[10px]"
      title={label}
    >
      <span className="text-ink-faint">{label.slice(0, 4)}</span>
      <span className="stat text-ink">{value === null ? "—" : value.toFixed(2)}</span>
    </span>
  );
}
