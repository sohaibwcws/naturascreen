"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { PopulationChart } from "@/components/charts/population-chart";
import { useSimulationStream } from "@/lib/stream";
import { cn, fmt } from "@/lib/utils";

// r3f touches `window`, so the canvas must not server-render.
const TumorView = dynamic(() => import("./tumor-view").then((m) => m.TumorView), {
  ssr: false,
  loading: () => <div className="panel h-[420px] animate-pulse-soft" />,
});

const LEGEND = [
  { label: "dividing", color: "bg-cell-dividing" },
  { label: "stressed", color: "bg-cell-stressed" },
  { label: "dying", color: "bg-cell-dying" },
];

export function SimulationPlayer({ streamPath }: { streamPath: string | null }) {
  const { meta, frames, end, status, error } = useSimulationStream(streamPath);
  const [index, setIndex] = useState(0);
  const [following, setFollowing] = useState(true);
  const [playing, setPlaying] = useState(false);

  const lastIndex = frames.length - 1;

  // Follow the live edge while streaming.
  useEffect(() => {
    if (following && lastIndex >= 0) setIndex(lastIndex);
  }, [lastIndex, following]);

  useEffect(() => {
    if (status === "done") setFollowing(false);
  }, [status]);

  // Replay timer (after the stream completes).
  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => {
      setIndex((i) => {
        if (i >= lastIndex) {
          setPlaying(false);
          return i;
        }
        return i + 1;
      });
    }, 1000 / 12);
    return () => clearInterval(id);
  }, [playing, lastIndex]);

  const frame = frames[index] ?? null;
  const notice = meta?.illustrative_notice ?? null;

  return (
    <div className="space-y-4">
      {error && (
        <div className="panel panel-pad text-sm text-danger">
          {error}. Is the API running and the stack up?
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
        <TumorView frame={frame} notice={notice} />
        <PopulationChart frames={frames} upTo={index} />
      </div>

      <div className="panel panel-pad space-y-3">
        <div className="flex flex-wrap items-center gap-4">
          <button
            className="btn btn-primary"
            disabled={frames.length === 0}
            onClick={() => {
              setFollowing(false);
              if (index >= lastIndex) setIndex(0);
              setPlaying((p) => !p);
            }}
          >
            {playing ? "Pause" : status === "done" ? "Replay" : "Play"}
          </button>
          <input
            type="range"
            min={0}
            max={Math.max(0, lastIndex)}
            value={index}
            onChange={(e) => {
              setFollowing(false);
              setPlaying(false);
              setIndex(Number(e.target.value));
            }}
            className="h-1 flex-1 cursor-pointer accent-accent"
          />
          <span className="stat text-xs text-ink-faint">
            t = {frame?.t ?? 0} / {meta?.steps ?? "—"}
          </span>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex gap-3">
            {LEGEND.map((l) => (
              <span key={l.label} className="flex items-center gap-1.5 text-ink-muted">
                <span className={cn("h-2 w-2 rounded-full", l.color)} /> {l.label}
              </span>
            ))}
          </div>
          <div className="flex gap-5 stat">
            <Stat label="with compound" value={frame ? String(frame.population) : "—"} accent />
            <Stat label="untreated" value={frame ? String(frame.baseline_population) : "—"} />
            <Stat
              label="reduction vs untreated"
              value={end ? `${fmt(end.reduction_pct, 1)}%` : "—"}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <span className="flex flex-col">
      <span className="label">{label}</span>
      <span className={cn("text-sm", accent ? "text-accent" : "text-ink")}>{value}</span>
    </span>
  );
}
