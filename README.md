# NaturaScreen

**An open-source platform to help researchers fight cancer with simulation and compound
screening.** NaturaScreen screens open natural compounds against cancer proteins and
tumor-specific neoantigens through molecular docking, ML response prediction, and a live
agent-based tumor simulation — and ranks candidates as **research hypotheses** that sharpen
through a lab-result feedback loop.

> **It does not produce cures, and it says so everywhere.** Every output is a research
> hypothesis for laboratory investigation — not a treatment, cure, dose, or medical
> recommendation, and not validated for human use. The disclaimer is wired into the schema,
> the API, and every export; it cannot be turned off. If you or someone you love is facing
> cancer, please work with qualified clinicians.

## Why I built this

I'm **Sohaib Khan**. I was diagnosed with **oral squamous cell carcinoma** ("SSC"). Going
looking for answers, I found a field doing extraordinary science behind expensive paywalls,
scattered databases, and command-line tools most people can't touch. So I built NaturaScreen:
an open platform that puts real compound screening, neoantigen targeting, and tumor
simulation in one place anyone can run — to help researchers, students, and the curious test
more ideas, faster, against cancer, with honest tools and open data. No one lab fights cancer
alone; this is my contribution to the many who do.

## Two honesty boundaries, enforced by the type system

1. **The cure boundary** (`DISCLAIMER`) — every results/report/export carries it via a
   non-optional Pydantic field; the frontend report cannot render without it.
2. **The illustration boundary** (`SIMULATION_NOTICE`) — the agent simulation is a
   *qualitative illustration of the effectiveness score, not a prediction of tumor
   response*. There is no validated function mapping a binding score to a tumor growth rate;
   that mapping is one named, documented, illustrative function (`HeuristicEffectTransfer`).
   The notice rides on the stream's opening envelope and every frame, and the 3D viewer
   refuses to render cells without showing it.

## Scientific pipeline

| Stage | What it does | Tool | Runs on |
|---|---|---|---|
| Compound library | Natural products → SMILES + RDKit descriptors | COCONUT (CC0) + RDKit | **everywhere** |
| Docking | Binding affinity vs. a curated pocket box | AutoDock Vina (+ Meeko) | Linux worker / any host with a Vina binary¹ |
| Neoantigen | Peptide–MHC presentation %rank | MHCflurry | **everywhere** (after `make data-mhcflurry`) |
| Response | Predicted cell-line ln(IC50) + OOD flag | XGBoost on GDSC1 | **everywhere** (after `make data-response`) |
| Simulation | Agent-based tumor population (illustrative) | NumPy | **everywhere** |

¹ Vina's Python wheel is Linux/x86; the adapter also drives the Vina **CLI** binary, so it
runs in the Docker worker or on any host where `vina` is on PATH. (Apple-silicon hosts need
the Linux worker or Rosetta + the x86 binary.) When unprovisioned, every adapter reports
`unavailable` — **never a fabricated number**.

### Honest design choices
- **Scoring** combines only the sub-scores actually computed, each normalized via a *fixed,
  documented reference window* (exposed per-compound in the report). Missing sub-scores are
  excluded and weights renormalized — never imputed as 0. The illustrative `simulation` term
  defaults to weight **0** to avoid double-counting.
- **Response OOD**: the model is trained on synthetic-drug screens (GDSC) and is
  out-of-distribution for most natural products; each prediction carries a nearest-neighbour
  Tanimoto applicability flag, surfaced in the report.

### Validated, not just wired (what has actually been executed)
- **Docking**: a real AutoDock Vina dock of the 1iep receptor / imatinib benchmark returns
  **−13.28 kcal/mol** (the published value) on `linux/amd64` — the worker platform.
- **Neoantigen**: live MHCflurry ranks CMV/flu epitopes as strong binders (%rank 0.02–0.13)
  and poly-alanine as a non-binder (~9.5), as expected.
- **Response**: trained on real GDSC1 (307 drugs, 120k cell-line×drug rows). Honest dual CV —
  **random-split R²≈0.76** (skill at the IC50 regression task) but **leave-compounds-out
  R²≈0.05** (the truthful metric for ranking an *unseen* compound: structure-only
  generalization to new natural products is genuinely hard). Both are exposed at `/meta`.
- **Orchestration**: the full Postgres + in-container Alembic migration + COCONUT ingestion
  + API path runs under Docker (validated via colima).

## Quickstart (local, Docker)

```bash
git clone https://github.com/sohaibwcws/naturascreen && cd naturascreen
cp .env.example .env
make up                       # postgres, redis, api, worker, beat, web
make migrate
make ingest-compounds n=300   # live, CC0 natural products from COCONUT
open http://localhost:3000
```

No Docker? A no-service local run (SQLite + the synchronous experiment path) works too — see
`docs/`. Provision the real adapters:

```bash
make curate-targets   # curated cancer targets with cited docking boxes
make data-mhcflurry   # fetch MHCflurry models  (set WORKER_EXTRAS=docking,neoantigen,response)
make data-response    # build a real GDSC1 (SMILES, LN_IC50) set + train XGBoost
```

## Production (HTTPS)

`deploy/docker-compose.prod.yml` runs the full stack behind **Caddy** (automatic TLS via
Let's Encrypt) with Postgres, Redis, Celery + beat, a production Next.js build, **API-key
auth** on write/compute endpoints, and **Redis-backed rate limiting**.

```bash
cp deploy/.env.example deploy/.env   # set APP_DOMAIN, API_DOMAIN, POSTGRES_PASSWORD, NATURASCREEN_API_KEYS
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --build
```

## Tests

```bash
make test       # full backend suite (Vina/MHCflurry-gated tests skip without those tools)
make test-core  # dependency-light core logic (sim, scoring, normalization, disclaimer)
cd web && npx tsc --noEmit
```

## Support the mission

NaturaScreen is free and open. The best way to help fight cancer with it:
- ★ **Star & share** the repository — reach is how open science compounds.
- ⚙ **Contribute** — better models, curated targets, datasets, validated lab results.
- 🔬 **Bring real data** — submit lab results so the model learns what holds up in the dish.

## Tech stack & data

FastAPI · SQLAlchemy 2 (async) · Celery + Redis · RDKit · AutoDock Vina + Meeko · MHCflurry ·
XGBoost · Next.js 15 · react-three-fiber · D3 · Tailwind. Data: COCONUT 2.0 (CC0), GDSC1
(cancerrxgene.org), RCSB PDB. Docking pocket boxes are hand-curated with literature citations.

---

Created & Developed by **[Sohaib Khan](https://sohaib.com)**. A mission to help find a cancer cure.
