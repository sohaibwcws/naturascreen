"use client";

import { useState } from "react";

export interface PredictRequest {
  tumor_type: string;
  hla_alleles: string[];
  peptides: string[];
}

/**
 * Controlled form for an MHCflurry presentation request: a tumor/cohort label,
 * comma-separated HLA class I alleles (rendered back as chips), and one peptide
 * per line. Validates locally, then hands a clean request body to `onSubmit`.
 */
export function PredictForm({
  busy,
  onSubmit,
}: {
  busy: boolean;
  onSubmit: (body: PredictRequest) => void;
}) {
  const [tumorType, setTumorType] = useState("");
  const [allelesRaw, setAllelesRaw] = useState("HLA-A*02:01");
  const [peptidesRaw, setPeptidesRaw] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const alleles = splitTokens(allelesRaw, /[,\n]/);
  const peptides = splitTokens(peptidesRaw, /\n/);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    if (!tumorType.trim()) {
      setLocalError("Enter a tumor type / cohort label.");
      return;
    }
    if (alleles.length === 0) {
      setLocalError("Add at least one HLA allele, e.g. HLA-A*02:01.");
      return;
    }
    if (peptides.length === 0) {
      setLocalError("Add at least one peptide (one per line).");
      return;
    }
    onSubmit({ tumor_type: tumorType.trim(), hla_alleles: alleles, peptides });
  };

  return (
    <form onSubmit={submit} className="panel panel-pad space-y-4">
      <h2 className="label">Predict presentation</h2>

      <label className="block space-y-1.5">
        <span className="label">Tumor type / cohort</span>
        <input
          className="input"
          placeholder="e.g. melanoma"
          value={tumorType}
          onChange={(e) => setTumorType(e.target.value)}
        />
      </label>

      <label className="block space-y-1.5">
        <span className="label">HLA class I alleles (comma-separated)</span>
        <input
          className="input font-mono"
          placeholder="HLA-A*02:01, HLA-B*07:02"
          value={allelesRaw}
          onChange={(e) => setAllelesRaw(e.target.value)}
        />
        {alleles.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {alleles.map((a) => (
              <span key={a} className="chip font-mono">
                {a}
              </span>
            ))}
          </div>
        )}
      </label>

      <label className="block space-y-1.5">
        <span className="label">Candidate peptides (one per line)</span>
        <textarea
          className="input min-h-[8rem] font-mono"
          placeholder={"SIINFEKL\nGADGVGKSA\nVVGADGVGK"}
          value={peptidesRaw}
          onChange={(e) => setPeptidesRaw(e.target.value)}
        />
        <span className="text-xs text-ink-faint">
          {peptides.length} peptide{peptides.length === 1 ? "" : "s"} · 8-11mers recommended
        </span>
      </label>

      {localError && <p className="text-sm text-danger">{localError}</p>}

      <button type="submit" className="btn btn-primary w-full" disabled={busy}>
        {busy ? "Predicting…" : "Predict presentation"}
      </button>
    </form>
  );
}

/** Split on the given separator, trim, drop blanks, and de-duplicate (stable order). */
function splitTokens(raw: string, sep: RegExp): string[] {
  return Array.from(
    new Set(
      raw
        .split(sep)
        .map((s) => s.trim())
        .filter(Boolean),
    ),
  );
}
