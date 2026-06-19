"use client";

import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import type { CandidateReport as Report } from "@/lib/types";
import { fmt } from "@/lib/utils";

export function CandidateReport({ experimentId }: { experimentId: number }) {
  const { data, error } = useAsync<Report>(
    () => api.get(`/experiments/${experimentId}/report`),
    [experimentId],
  );

  if (error) return null; // no ranking yet
  if (!data) return <div className="panel h-40 animate-pulse-soft" />;

  return (
    <div className="panel panel-pad space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <span className="label">Candidate hypothesis · rank {data.rank}</span>
          <h3 className="mt-1 text-lg font-medium">{data.compound.name}</h3>
          <p className="font-mono text-[11px] text-ink-faint">{data.compound.coconut_id}</p>
        </div>
        <div className="flex gap-2">
          <a className="btn" href={`${api.base}/experiments/${experimentId}/report.pdf`} download>
            PDF
          </a>
          <a className="btn" href={`${api.base}/experiments/${experimentId}/report`} target="_blank" rel="noreferrer">
            JSON
          </a>
        </div>
      </div>

      <div>
        <span className="label">Predicted mechanism</span>
        <p className="mt-1 text-sm leading-relaxed text-ink-muted">{data.predicted_mechanism}</p>
      </div>

      <div className="flex flex-wrap gap-6 text-sm">
        <span className="flex flex-col">
          <span className="label">combined score</span>
          <span className="stat text-accent">{fmt(data.combined_score, 3)}</span>
        </span>
        {data.target && (
          <span className="flex flex-col">
            <span className="label">target</span>
            <span className="text-ink">{data.target.gene ?? data.target.pdb_id ?? "—"}</span>
          </span>
        )}
        {data.simulation && (
          <span className="flex flex-col">
            <span className="label">illustrative reduction</span>
            <span className="stat text-ink">{fmt(data.simulation.reduction_pct, 1)}%</span>
          </span>
        )}
      </div>

      <div>
        <span className="label">Caveats</span>
        <ul className="mt-1 space-y-1.5 text-xs leading-relaxed text-ink-muted">
          {data.caveats.map((c, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-warn">•</span>
              <span>{c}</span>
            </li>
          ))}
        </ul>
      </div>

      <p className="border-t border-base-750 pt-3 text-[11px] leading-relaxed text-ink-faint">
        {data.disclaimer}
      </p>
    </div>
  );
}
