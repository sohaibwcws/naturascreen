"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import type { Compound, ExperimentSummary, TargetOut } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS_COLOR: Record<string, string> = {
  completed: "text-cell-dividing border-cell-dividing/40",
  running: "text-accent border-accent/40",
  queued: "text-warn border-warn/40",
  failed: "text-danger border-danger/40",
  created: "text-ink-muted border-base-700",
};

export default function ExperimentsPage() {
  const router = useRouter();
  const list = useAsync<ExperimentSummary[]>(() => api.get("/experiments"), []);
  const targets = useAsync<TargetOut[]>(() => api.get("/targets"), []);

  const [selected, setSelected] = useState<Compound[]>([]);
  const [targetId, setTargetId] = useState<number | null>(null);
  const [seed, setSeed] = useState(0);
  const [weights, setWeights] = useState({ binding: 0.4, neoantigen: 0.25, response: 0.35 });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const createAndRun = async () => {
    setErr(null);
    if (selected.length === 0) {
      setErr("Add at least one compound.");
      return;
    }
    setBusy(true);
    try {
      const exp = await api.post<ExperimentSummary>("/experiments", {
        compound_set: selected.map((c) => c.id),
        target_id: targetId,
        weights: { ...weights, simulation: 0 },
        seed,
      });
      await api.post(`/experiments/${exp.id}/run?sync=true`, {});
      router.push(`/experiments/${exp.id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed to create experiment");
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Experiments</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Pick compounds and a target, set the scoring weights, and screen. Results are ranked
          research hypotheses.
        </p>
      </header>

      <section className="panel panel-pad space-y-4">
        <h2 className="label">New experiment</h2>
        <CompoundPicker selected={selected} onChange={setSelected} />

        <div className="grid gap-4 sm:grid-cols-3">
          <label className="space-y-1.5">
            <span className="label">Target (optional)</span>
            <select
              className="input"
              value={targetId ?? ""}
              onChange={(e) => setTargetId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">— none —</option>
              {targets.data?.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.gene ?? t.pdb_id ?? `target ${t.id}`} {t.dockable ? "" : "(not dockable)"}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1.5">
            <span className="label">Seed</span>
            <input
              type="number"
              className="input"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
            />
          </label>
          <div className="flex items-end">
            <button className="btn btn-primary w-full" disabled={busy} onClick={createAndRun}>
              {busy ? "Running…" : "Create & run"}
            </button>
          </div>
        </div>

        <details className="text-sm">
          <summary className="cursor-pointer text-ink-muted">Scoring weights</summary>
          <div className="mt-3 grid gap-4 sm:grid-cols-3">
            {(["binding", "neoantigen", "response"] as const).map((k) => (
              <label key={k} className="space-y-1.5">
                <span className="label capitalize">{k}</span>
                <input
                  type="number"
                  step={0.05}
                  min={0}
                  className="input"
                  value={weights[k]}
                  onChange={(e) => setWeights((w) => ({ ...w, [k]: Number(e.target.value) }))}
                />
              </label>
            ))}
          </div>
          <p className="mt-2 text-xs text-ink-faint">
            Simulation weight is fixed at 0: its reduction is derived from the other sub-scores,
            so weighting it would double-count (it is illustrative, not an input).
          </p>
        </details>

        {err && <p className="text-sm text-danger">{err}</p>}
      </section>

      <section className="space-y-2">
        <h2 className="label">Recent experiments</h2>
        {list.data && list.data.length > 0 ? (
          <ul className="divide-y divide-base-750 overflow-hidden rounded-lg border border-base-700">
            {list.data.map((e) => (
              <li key={e.id}>
                <Link
                  href={`/experiments/${e.id}`}
                  className="flex items-center justify-between bg-base-800 px-4 py-3 text-sm hover:bg-base-750"
                >
                  <span>
                    Experiment #{e.id}
                    <span className="ml-2 text-xs text-ink-faint">
                      {e.compound_set.length} compounds
                    </span>
                  </span>
                  <span
                    className={cn(
                      "chip border",
                      STATUS_COLOR[e.status] ?? "text-ink-muted border-base-700",
                    )}
                  >
                    {e.status}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-ink-faint">No experiments yet.</p>
        )}
      </section>
    </div>
  );
}

function CompoundPicker({
  selected,
  onChange,
}: {
  selected: Compound[];
  onChange: (next: Compound[]) => void;
}) {
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  const { data } = useAsync(
    () => (debounced ? api.compounds({ q: debounced, limit: 8 }) : Promise.resolve(null)),
    [debounced],
  );

  const add = (c: Compound) => {
    if (!selected.some((s) => s.id === c.id)) onChange([...selected, c]);
  };

  return (
    <div className="space-y-2">
      <span className="label">Compounds ({selected.length})</span>
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selected.map((c) => (
            <span key={c.id} className="chip">
              {c.name}
              <button
                className="text-ink-faint hover:text-danger"
                onClick={() => onChange(selected.filter((s) => s.id !== c.id))}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      <input
        className="input"
        placeholder="Search compounds to add…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      {data && data.items.length > 0 && (
        <ul className="max-h-44 overflow-auto rounded-md border border-base-700">
          {data.items.map((c) => (
            <li key={c.id}>
              <button
                className="flex w-full items-center justify-between px-3 py-1.5 text-left text-sm hover:bg-base-750"
                onClick={() => add(c)}
              >
                <span className="truncate">{c.name}</span>
                <span className="chip font-mono">{c.coconut_id}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
