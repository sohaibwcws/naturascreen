"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { SimulationPlayer } from "@/components/tumor/simulation-player";
import { RankingTable } from "@/components/experiments/ranking-table";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import type { ExperimentResults } from "@/lib/types";
import { fmt } from "@/lib/utils";

export default function ExperimentDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [reloadKey, setReloadKey] = useState(0);

  const { data, error } = useAsync<ExperimentResults>(
    () => api.get(`/experiments/${id}/results`),
    [id, reloadKey],
  );

  const status = data?.experiment.status;
  const completed = status === "completed";

  const rerun = async () => {
    await api.post(`/experiments/${id}/run?sync=true`, {});
    setReloadKey((k) => k + 1);
  };

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Experiment #{id}</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Status: <span className="text-ink">{status ?? "…"}</span>
          </p>
        </div>
        <button className="btn" onClick={rerun}>
          Re-run
        </button>
      </header>

      {error && <div className="panel panel-pad text-sm text-danger">{error}</div>}

      {data && (
        <div className="panel panel-pad border-l-2 border-l-warn/50 text-xs leading-relaxed text-ink-muted">
          {data.disclaimer}
        </div>
      )}

      <section className="space-y-2">
        <h2 className="label">Tumor simulation — top compound</h2>
        <SimulationPlayer streamPath={completed ? `/experiments/${id}/stream?fps=14` : null} />
        {data?.simulation && (
          <div className="panel panel-pad flex flex-wrap gap-6 text-sm">
            <Metric label="untreated final" value={String(data.simulation.baseline_population)} />
            <Metric label="treated final" value={String(data.simulation.final_population)} />
            <Metric
              label="illustrative reduction"
              value={`${fmt(data.simulation.reduction_pct, 1)}%`}
              accent
            />
          </div>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="label">Ranked candidates</h2>
        {data && data.ranked.length > 0 ? (
          <RankingTable rows={data.ranked} />
        ) : (
          <p className="text-sm text-ink-faint">
            No scores yet. {status !== "completed" && "Run the experiment to rank candidates."}
          </p>
        )}
      </section>
    </div>
  );
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="flex flex-col">
      <span className="label">{label}</span>
      <span className={`stat text-lg ${accent ? "text-accent" : "text-ink"}`}>{value}</span>
    </div>
  );
}
