"use client";

import { useState } from "react";
import { SimulationPlayer } from "@/components/tumor/simulation-player";

export default function SimulatePage() {
  const [effectiveness, setEffectiveness] = useState(0.6);
  const [seed, setSeed] = useState(0);
  const [population, setPopulation] = useState(400);
  const [runId, setRunId] = useState(0);
  const [path, setPath] = useState<string | null>(null);

  const run = () => {
    const next = runId + 1;
    setRunId(next);
    setPath(
      `/simulate/stream?effectiveness=${effectiveness}&seed=${seed}` +
        `&population=${population}&steps=120&fps=14&_=${next}`,
    );
  };

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Simulation explorer</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-muted">
          Watch the agent-based tumor model under the illustrative effect transfer. This is a
          sandbox for understanding the model dynamics — the effectiveness here is a value you
          choose, <span className="text-warn">not a prediction for any compound.</span>
        </p>
      </header>

      <div className="panel panel-pad grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <label className="space-y-1.5">
          <span className="label">Effectiveness (illustrative)</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={effectiveness}
            onChange={(e) => setEffectiveness(Number(e.target.value))}
            className="h-1 w-full cursor-pointer accent-accent"
          />
          <span className="stat text-sm text-accent">{effectiveness.toFixed(2)}</span>
        </label>
        <label className="space-y-1.5">
          <span className="label">Seed</span>
          <input
            type="number"
            value={seed}
            onChange={(e) => setSeed(Number(e.target.value))}
            className="input"
          />
        </label>
        <label className="space-y-1.5">
          <span className="label">Initial population</span>
          <input
            type="number"
            min={20}
            max={1500}
            value={population}
            onChange={(e) => setPopulation(Number(e.target.value))}
            className="input"
          />
        </label>
        <div className="flex items-end">
          <button className="btn btn-primary w-full" onClick={run}>
            Run simulation
          </button>
        </div>
      </div>

      {path ? (
        <SimulationPlayer streamPath={path} />
      ) : (
        <div className="panel grid h-[420px] place-items-center text-sm text-ink-faint">
          Set parameters and run to stream a live simulation.
        </div>
      )}
    </div>
  );
}
