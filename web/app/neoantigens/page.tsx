"use client";

import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { PredictForm, type PredictRequest } from "@/components/neoantigens/predict-form";
import { cn, fmt } from "@/lib/utils";

interface Prediction {
  id: number;
  tumor_type: string;
  peptide: string;
  mhc_allele: string;
  affinity_nM: number | null;
  presentation_rank: number | null;
  binder_class: string;
}

interface PredictResponse {
  note: string;
  strong_rank_threshold: number;
  weak_rank_threshold: number;
  count: number;
  predictions: Prediction[];
}

// Binder class -> emphasis colour. Strong = dividing (green), weak = stressed (amber);
// both shared with the WebGL cell-state palette so the whole app reads consistently.
const CLASS_COLOR: Record<string, string> = {
  strong: "text-cell-dividing",
  weak: "text-cell-stressed",
  "non-binder": "text-ink-muted",
  unscored: "text-ink-faint",
};

export default function NeoantigensPage() {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notProvisioned, setNotProvisioned] = useState(false);

  const runPrediction = async (body: PredictRequest) => {
    setBusy(true);
    setError(null);
    setNotProvisioned(false);
    try {
      const data = await api.post<PredictResponse>("/neoantigens/predict", body);
      setResult(data);
    } catch (e) {
      if (e instanceof ApiError && e.status === 503) {
        setNotProvisioned(true);
        setResult(null);
      } else {
        setError(e instanceof Error ? e.message : "prediction failed");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Neoantigen presentation</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-muted">
          Predict peptide–MHC class I presentation with{" "}
          <span className="text-ink">MHCflurry</span>. A low presentation %rank flags a candidate
          tumor epitope — never a confirmed target on its own.
        </p>
      </header>

      <div className="panel panel-pad border-warn/30 bg-warn/5 text-sm text-ink-muted">
        <span className="font-medium text-warn">Candidate targets only.</span>{" "}
        Neoantigen presentation predictions have frequent false positives. A strong-looking %rank
        marks a peptide for wet-lab validation (immunopeptidomics, T-cell assays), not a presented
        neoantigen — and nothing here is a treatment claim.
      </div>

      <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
        <PredictForm busy={busy} onSubmit={runPrediction} />

        <div className="space-y-4">
          {notProvisioned && <NotProvisioned />}
          {error && (
            <div className="panel panel-pad text-sm text-danger">
              Prediction failed: {error}
            </div>
          )}
          {result ? (
            <Results data={result} />
          ) : (
            !notProvisioned && !error && <EmptyState />
          )}
        </div>
      </div>
    </div>
  );
}

function Results({ data }: { data: PredictResponse }) {
  if (data.predictions.length === 0) {
    return (
      <div className="panel panel-pad text-sm text-ink-muted">
        No predictions returned for those peptides and alleles.
      </div>
    );
  }

  const strong = data.predictions.filter((p) => p.binder_class === "strong").length;
  const weak = data.predictions.filter((p) => p.binder_class === "weak").length;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-ink-faint">{data.count} predictions</span>
        <span className="chip border border-cell-dividing/40 text-cell-dividing">
          {strong} strong (%rank ≤ {fmt(data.strong_rank_threshold, 1)})
        </span>
        <span className="chip border border-cell-stressed/40 text-cell-stressed">
          {weak} weak (≤ {fmt(data.weak_rank_threshold, 1)})
        </span>
      </div>

      <div className="panel overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-base-700 text-left text-xs text-ink-faint">
              <th className="px-3 py-2 font-medium">Peptide</th>
              <th className="px-3 py-2 font-medium">Allele</th>
              <th className="px-3 py-2 text-right font-medium">%rank</th>
              <th className="px-3 py-2 text-right font-medium">Affinity (nM)</th>
              <th className="px-3 py-2 font-medium">Class</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-base-750">
            {data.predictions.map((p) => {
              const color = CLASS_COLOR[p.binder_class] ?? "text-ink";
              return (
                <tr key={p.id} className="hover:bg-base-750/50">
                  <td className="px-3 py-2 font-mono">{p.peptide}</td>
                  <td className="px-3 py-2 font-mono text-ink-muted">{p.mhc_allele}</td>
                  <td className={cn("stat px-3 py-2 text-right", color)}>
                    {fmt(p.presentation_rank, 3)}
                  </td>
                  <td className="stat px-3 py-2 text-right text-ink-muted">
                    {fmt(p.affinity_nM, 1)}
                  </td>
                  <td className={cn("px-3 py-2 capitalize", color)}>{p.binder_class}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function NotProvisioned() {
  return (
    <div className="panel panel-pad space-y-2 border-warn/40 bg-warn/5">
      <p className="text-sm font-medium text-warn">MHCflurry is not provisioned</p>
      <p className="text-sm text-ink-muted">
        The presentation models are a large download that is not bundled. Fetch them with{" "}
        <code className="font-mono text-xs text-accent">make data-mhcflurry</code> and try again.
        Predictions are never fabricated, so this returns nothing rather than guess.
      </p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="panel grid min-h-[12rem] place-items-center text-sm text-ink-faint">
      Enter alleles and candidate peptides, then predict to see ranked presentation.
    </div>
  );
}
