"use client";

import Link from "next/link";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import type { Meta } from "@/lib/types";
import { cn } from "@/lib/utils";

const STAGES = [
  { n: 1, name: "Compound library", desc: "Natural products from COCONUT (CC0)." },
  { n: 2, name: "Neoantigen targeting", desc: "Tumor mutations → peptide–MHC binding." },
  { n: 3, name: "Molecular docking", desc: "Binding affinity vs. cancer targets." },
  { n: 4, name: "Response prediction", desc: "Predicted cell-line response." },
  { n: 5, name: "Tumor simulation", desc: "Agent-based, illustrative only." },
];

export default function DashboardPage() {
  const { data: meta } = useAsync<Meta>(() => api.meta(), []);

  return (
    <div className="mx-auto max-w-5xl space-y-10">
      <section className="space-y-4 pt-2">
        <span className="chip">NaturaScreen · open-source · research hypotheses only</span>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          Screen natural compounds against cancer,{" "}
          <span className="text-accent">honestly.</span>
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-ink-muted">
          NaturaScreen docks open natural products against cancer proteins and tumor
          neoantigens, predicts cell-line response, and shows the predicted effect on a
          simulated tumor in real time — then ranks candidates as hypotheses for the lab. It
          does not produce cures, and it says so everywhere.
        </p>
        <p className="max-w-2xl text-sm leading-relaxed text-ink-muted">
          Built by Sohaib Khan after an oral squamous cell carcinoma diagnosis — a tool to
          help researchers fight cancer with open simulation and compound screening.{" "}
          <Link href="/about" className="text-accent hover:underline">
            Read the story →
          </Link>
        </p>
        <div className="flex flex-wrap gap-3 pt-1">
          <Link href="/experiments" className="btn btn-primary">
            Build an experiment
          </Link>
          <Link href="/simulate" className="btn">
            Live simulator
          </Link>
          <Link href="/about" className="btn">
            About &amp; support
          </Link>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="label">Pipeline</h2>
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {STAGES.map((s) => (
            <li key={s.n} className="panel panel-pad">
              <div className="mb-2 font-mono text-xs text-accent">0{s.n}</div>
              <div className="text-sm font-medium">{s.name}</div>
              <div className="mt-1 text-xs leading-relaxed text-ink-faint">{s.desc}</div>
            </li>
          ))}
        </ol>
      </section>

      <section className="space-y-3">
        <h2 className="label">Scientific adapters</h2>
        <p className="text-xs text-ink-faint">
          Real tools, not fakes. When a tool is not provisioned its results are reported as
          unavailable — never fabricated.
        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          {meta
            ? (["docking", "neoantigen", "response"] as const).map((key) => {
                const a = meta.adapters[key];
                return (
                  <div key={key} className="panel panel-pad flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium capitalize">{key}</div>
                      <div className="text-xs text-ink-faint">{a.tool}</div>
                    </div>
                    <span
                      className={cn(
                        "chip",
                        a.available
                          ? "border-cell-dividing/40 text-cell-dividing"
                          : "border-base-700 text-ink-faint",
                      )}
                    >
                      <span
                        className={cn(
                          "h-1.5 w-1.5 rounded-full",
                          a.available ? "bg-cell-dividing" : "bg-ink-faint",
                        )}
                      />
                      {a.available ? "ready" : "unavailable"}
                    </span>
                  </div>
                );
              })
            : Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="panel panel-pad h-16 animate-pulse-soft" />
              ))}
        </div>
      </section>
    </div>
  );
}
