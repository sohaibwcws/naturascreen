"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import type { Compound, CompoundPage } from "@/lib/types";
import { cn, fmt } from "@/lib/utils";

const PAGE_SIZE = 24;

export default function CompoundsPage() {
  const [rawQuery, setRawQuery] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<Compound | null>(null);

  // Debounce the search box; reset to page 0 on a new query.
  useEffect(() => {
    const t = setTimeout(() => {
      setQuery(rawQuery.trim());
      setPage(0);
    }, 300);
    return () => clearTimeout(t);
  }, [rawQuery]);

  const { data, error, loading } = useAsync<CompoundPage>(
    () => api.compounds({ q: query || undefined, limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
    [query, page],
  );

  const pageCount = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Compound library</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Natural products from COCONUT (CC0). Ingest more with{" "}
            <code className="font-mono text-xs text-accent">make ingest-compounds</code>.
          </p>
        </div>
        <div className="text-right text-xs text-ink-faint">
          {data ? `${data.total.toLocaleString()} compounds` : "—"}
        </div>
      </header>

      <input
        className="input"
        placeholder="Search by name, COCONUT id, or InChIKey…"
        value={rawQuery}
        onChange={(e) => setRawQuery(e.target.value)}
      />

      {error && (
        <div className="panel panel-pad text-sm text-danger">
          Could not reach the API: {error}. Is the stack up (<code>make up</code>)?
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <div>
          {loading && !data ? (
            <SkeletonGrid />
          ) : data && data.items.length === 0 ? (
            <div className="panel panel-pad text-sm text-ink-muted">
              No compounds yet. Run <code className="font-mono text-accent">make ingest-compounds n=200</code>{" "}
              to populate the library from COCONUT.
            </div>
          ) : (
            <ul className="grid gap-3 sm:grid-cols-2">
              {data?.items.map((c) => (
                <li key={c.id}>
                  <button
                    onClick={() => setSelected(c)}
                    className={cn(
                      "panel panel-pad w-full text-left transition hover:border-accent/40",
                      selected?.id === c.id && "border-accent/60",
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="line-clamp-2 text-sm font-medium">{c.name}</span>
                      <span className="chip flex-none font-mono">{c.coconut_id}</span>
                    </div>
                    <div className="mt-3 flex gap-4 text-xs text-ink-faint">
                      <span className="stat">MW {fmt(num(c, "molecular_weight"), 1)}</span>
                      <span className="stat">logP {fmt(num(c, "logp"), 2)}</span>
                      <span className="stat">QED {fmt(num(c, "qed"), 2)}</span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {data && data.total > PAGE_SIZE && (
            <div className="mt-5 flex items-center justify-between text-sm">
              <button className="btn" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                ← Prev
              </button>
              <span className="text-xs text-ink-faint">
                Page {page + 1} / {pageCount}
              </span>
              <button
                className="btn"
                disabled={page + 1 >= pageCount}
                onClick={() => setPage((p) => p + 1)}
              >
                Next →
              </button>
            </div>
          )}
        </div>

        <div className="lg:sticky lg:top-4 lg:self-start">
          <CompoundDetail compound={selected} />
        </div>
      </div>
    </div>
  );
}

function num(c: Compound, key: string): number | undefined {
  const v = c.molecular_descriptors?.[key];
  return typeof v === "number" ? v : undefined;
}

function CompoundDetail({ compound }: { compound: Compound | null }) {
  if (!compound) {
    return (
      <div className="panel panel-pad text-sm text-ink-faint">
        Select a compound to see its structure, descriptors, and SMILES.
      </div>
    );
  }
  const d = compound.molecular_descriptors ?? {};
  const rows: [string, number | undefined][] = [
    ["Molecular weight", num(compound, "molecular_weight")],
    ["logP", num(compound, "logp")],
    ["TPSA", num(compound, "tpsa")],
    ["H-bond donors", num(compound, "h_bond_donors")],
    ["H-bond acceptors", num(compound, "h_bond_acceptors")],
    ["Rotatable bonds", num(compound, "rotatable_bonds")],
    ["Aromatic rings", num(compound, "aromatic_rings")],
    ["QED", num(compound, "qed")],
  ];
  return (
    <div className="panel panel-pad space-y-4 animate-fade-in">
      <div>
        <h2 className="text-sm font-medium leading-snug">{compound.name}</h2>
        <div className="mt-1 flex flex-wrap gap-1.5">
          <span className="chip font-mono">{compound.coconut_id}</span>
          <span className="chip">{compound.source_db}</span>
        </div>
      </div>
      {Object.keys(d).length > 0 && (
        <img
          src={`${api.base}/compounds/${compound.id}/structure.svg`}
          alt={`2D structure of ${compound.name}`}
          className="w-full rounded-md border border-base-700 bg-base-850"
          width={360}
          height={240}
        />
      )}
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
        {rows.map(([k, v]) => (
          <div key={k} className="flex items-center justify-between border-b border-base-750 py-1">
            <dt className="text-ink-faint">{k}</dt>
            <dd className="stat text-ink">{fmt(v, 2)}</dd>
          </div>
        ))}
      </dl>
      <div>
        <div className="label mb-1">SMILES</div>
        <code className="block break-all rounded-md border border-base-700 bg-base-850 p-2 font-mono text-[11px] text-ink-muted">
          {compound.smiles}
        </code>
      </div>
    </div>
  );
}

function SkeletonGrid() {
  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <li key={i} className="panel h-24 animate-pulse-soft" />
      ))}
    </ul>
  );
}
