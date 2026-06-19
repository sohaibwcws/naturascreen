"use client";

import { line, max, scaleLinear } from "d3";
import { useMemo } from "react";
import type { SimFrame } from "@/lib/types";

const W = 480;
const H = 240;
const M = { top: 16, right: 16, bottom: 28, left: 44 };

/**
 * Population over time: treated (accent) vs. untreated baseline (muted). Drawn up to
 * `upTo` so the curve grows with playback; scales are fixed to the full run so the axes
 * don't jump.
 */
export function PopulationChart({ frames, upTo }: { frames: SimFrame[]; upTo: number }) {
  const { treatedPath, baselinePath, x, y, maxT, maxPop } = useMemo(() => {
    const maxT = Math.max(1, frames.length - 1);
    const maxPop = Math.max(10, max(frames, (f) => Math.max(f.population, f.baseline_population)) ?? 10);
    const x = scaleLinear().domain([0, maxT]).range([M.left, W - M.right]);
    const y = scaleLinear().domain([0, maxPop]).range([H - M.bottom, M.top]);
    const visible = frames.slice(0, Math.max(1, upTo + 1));
    const mk = (key: "population" | "baseline_population") =>
      line<SimFrame>()
        .x((f) => x(f.t))
        .y((f) => y(f[key]))(visible) ?? "";
    return {
      treatedPath: mk("population"),
      baselinePath: mk("baseline_population"),
      x,
      y,
      maxT,
      maxPop,
    };
  }, [frames, upTo]);

  if (frames.length === 0) {
    return (
      <div className="panel grid h-[240px] place-items-center text-sm text-ink-faint">
        Population dynamics appear here once the simulation streams.
      </div>
    );
  }

  const yTicks = y.ticks(4);
  const xTicks = x.ticks(6);

  return (
    <div className="panel panel-pad">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="label">Population over time</h3>
        <div className="flex gap-3 text-[11px]">
          <span className="flex items-center gap-1.5 text-accent">
            <span className="h-0.5 w-3 bg-accent" /> with compound
          </span>
          <span className="flex items-center gap-1.5 text-ink-faint">
            <span className="h-0.5 w-3 border-t border-dashed border-ink-faint" /> untreated
          </span>
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="population chart">
        {yTicks.map((t) => (
          <g key={`y${t}`}>
            <line x1={M.left} x2={W - M.right} y1={y(t)} y2={y(t)} stroke="#1c2430" />
            <text x={M.left - 6} y={y(t)} dy="0.32em" textAnchor="end" className="fill-ink-faint text-[9px]">
              {t}
            </text>
          </g>
        ))}
        {xTicks.map((t) => (
          <text key={`x${t}`} x={x(t)} y={H - 10} textAnchor="middle" className="fill-ink-faint text-[9px]">
            {t}
          </text>
        ))}
        <path d={baselinePath} fill="none" stroke="#5f6b7c" strokeWidth={1.5} strokeDasharray="4 3" />
        <path d={treatedPath} fill="none" stroke="#3fd0c9" strokeWidth={2} />
      </svg>
    </div>
  );
}
