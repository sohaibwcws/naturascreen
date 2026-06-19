import Link from "next/link";
import { SITE } from "@/lib/site";

export const metadata = {
  title: "About — NaturaScreen | Created by Sohaib Khan",
  description:
    "NaturaScreen was created by Sohaib Khan after an oral squamous cell carcinoma diagnosis — an open-source platform to help researchers fight cancer with simulation and compound screening.",
};

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-12">
      {/* Story */}
      <section className="space-y-4 pt-2">
        <span className="chip">Why I built NaturaScreen</span>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          It started with a diagnosis.
        </h1>
        <div className="space-y-4 text-sm leading-relaxed text-ink-muted">
          <p>
            I&apos;m <span className="text-ink">Sohaib Khan</span>. I was diagnosed with{" "}
            <span className="text-ink">oral squamous cell carcinoma</span> — &ldquo;SSC&rdquo;.
            Hearing those words changes how you see everything. I went looking for answers, and
            what I found was a field doing extraordinary science behind expensive paywalls,
            scattered databases, and command-line tools that most people can never touch.
          </p>
          <p>
            So I built <span className="text-ink">NaturaScreen</span>: an open platform that puts
            real compound screening, neoantigen targeting, and tumor simulation into one place
            anyone can run. The goal isn&apos;t to claim a cure — it&apos;s to help researchers,
            students, and the curious test more ideas, faster, against cancer, with honest tools
            and open data.
          </p>
          <p>
            I can&apos;t fight this alone, and neither can any one lab. But thousands of people
            screening open compounds against real targets, sharing what holds up in the dish —
            that&apos;s a force. This is my contribution to it.
          </p>
        </div>
      </section>

      {/* The honest boundary */}
      <section className="panel panel-pad border-l-2 border-l-warn/50 space-y-2">
        <h2 className="text-sm font-medium text-warn">What this is — and what it is not</h2>
        <p className="text-sm leading-relaxed text-ink-muted">
          NaturaScreen produces <span className="text-ink">research hypotheses</span> for the lab.
          It is not a treatment, a cure, a dose, or medical advice, and nothing it outputs is
          validated for human use. A compound that looks promising in a model still needs
          cell-culture work, animal studies, and human clinical trials. If you or someone you
          love is facing cancer, please work with qualified clinicians. The honesty is the
          point — it&apos;s wired into the code so it can never be turned off.
        </p>
      </section>

      {/* What it does */}
      <section className="space-y-3">
        <h2 className="text-xl font-semibold tracking-tight">How it helps researchers</h2>
        <ul className="grid gap-3 sm:grid-cols-2">
          {[
            ["Open compound library", "Hundreds of thousands of natural products from COCONUT (CC0) — searchable, with structures and descriptors."],
            ["Neoantigen targeting", "Predict tumor-specific peptide–MHC presentation (MHCflurry) — the targets personalized vaccines aim at — and point compounds at them."],
            ["Molecular docking", "Score how strongly a compound binds a cancer target (AutoDock Vina) within a curated pocket."],
            ["Response prediction", "An ML model (XGBoost on GDSC) estimates cell-line potency — with honest out-of-distribution flags for natural products."],
            ["Live tumor simulation", "Watch an agent-based tumor respond in real time — an illustration of the score, never a prediction."],
            ["Lab-result feedback", "Real assay results flow back in and retrain the model, so the ranking sharpens against reality over time."],
          ].map(([title, body]) => (
            <li key={title} className="panel panel-pad">
              <div className="text-sm font-medium">{title}</div>
              <p className="mt-1 text-xs leading-relaxed text-ink-faint">{body}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* Potential */}
      <section className="space-y-3">
        <h2 className="text-xl font-semibold tracking-tight">The potential</h2>
        <p className="text-sm leading-relaxed text-ink-muted">
          Every result is a candidate to investigate, not a conclusion. But the search space of
          nature is enormous, and most of it has never been screened against most tumors. A free,
          open, honest tool lowers the cost of asking &ldquo;what if?&rdquo; — and the long road
          ahead points toward screening against a model of one patient&apos;s own tumor, with a
          robotic lab confirming the best picks on living tissue. That last mile — a real human,
          over real time — is exactly why clinical trials exist and why this tool will never
          replace them. It aims to make the candidate that reaches a trial far more likely to
          work.
        </p>
      </section>

      {/* How to run */}
      <section className="space-y-3">
        <h2 className="text-xl font-semibold tracking-tight">Run it yourself</h2>
        <p className="text-sm leading-relaxed text-ink-muted">
          It&apos;s open source. Bring up the whole stack locally with Docker:
        </p>
        <pre className="panel panel-pad overflow-x-auto font-mono text-xs leading-relaxed text-ink-muted">
{`git clone https://github.com/sohaibwcws/naturascreen && cd naturascreen
cp .env.example .env
make up                 # postgres, redis, api, worker, web
make migrate
make ingest-compounds n=300   # live, CC0 natural products
open http://localhost:3000`}
        </pre>
        <p className="text-xs text-ink-faint">
          Full setup, the scientific adapters, and the production (HTTPS) deploy are in the
          project README.
        </p>
      </section>

      {/* Support */}
      <section className="panel panel-pad space-y-4">
        <h2 className="text-xl font-semibold tracking-tight">
          Support the mission — help fight cancer
        </h2>
        <p className="text-sm leading-relaxed text-ink-muted">
          NaturaScreen is free and open, built in the open so the whole community can improve it.
          The best way to help is to use it, break it, and make it better:
        </p>
        <ul className="space-y-2 text-sm text-ink-muted">
          <li>★ <span className="text-ink">Star &amp; share</span> the repository — reach is how open science compounds.</li>
          <li>⚙ <span className="text-ink">Contribute</span> — better models, curated targets, validated lab results, new datasets.</li>
          <li>🔬 <span className="text-ink">Bring real data</span> — submit lab results so the model learns what holds up in the dish.</li>
          <li>📣 <span className="text-ink">Tell a researcher</span> who could put it to work.</li>
        </ul>
        <div className="flex flex-wrap gap-3 pt-1">
          <a href={SITE.repoUrl} target="_blank" rel="noopener noreferrer" className="btn btn-primary">
            View on GitHub
          </a>
          <a href={SITE.authorUrl} target="_blank" rel="noopener noreferrer" className="btn">
            Sohaib Khan — sohaib.com
          </a>
          <Link href="/simulate" className="btn">
            Try the simulator
          </Link>
        </div>
      </section>
    </div>
  );
}
