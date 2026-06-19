"use client";

import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import type { TargetOut } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function TargetsPage() {
  const { data, error } = useAsync<TargetOut[]>(() => api.get("/targets"), []);

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Cancer targets</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-muted">
          Proteins and neoantigen structures for docking. A target is only{" "}
          <span className="text-ink">dockable</span> once a human has curated its search box —
          a wrong or missing box gives confident garbage, so we never dock without one.
        </p>
      </header>

      {error && <div className="panel panel-pad text-sm text-danger">{error}</div>}

      {data && data.length === 0 && (
        <div className="panel panel-pad text-sm text-ink-muted">
          No targets curated yet. Load the curated registry with{" "}
          <code className="font-mono text-accent">make curate-targets</code>.
        </div>
      )}

      {data && data.length > 0 && (
        <ul className="grid gap-3 sm:grid-cols-2">
          {data.map((t) => (
            <li key={t.id} className="panel panel-pad">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-sm font-medium">{t.gene ?? t.pdb_id ?? `Target ${t.id}`}</div>
                  <div className="font-mono text-[11px] text-ink-faint">
                    {t.pdb_id ?? "—"} · {t.type}
                  </div>
                </div>
                <span
                  className={cn(
                    "chip border",
                    t.dockable
                      ? "border-cell-dividing/40 text-cell-dividing"
                      : "border-base-700 text-ink-faint",
                  )}
                >
                  {t.dockable ? "dockable" : "no box"}
                </span>
              </div>
              {t.description && (
                <p className="mt-2 text-xs leading-relaxed text-ink-muted">{t.description}</p>
              )}
              {t.box_source && (
                <p className="mt-2 text-[11px] text-ink-faint">Box: {t.box_source}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
