# NaturaScreen

Screen open-source **natural compounds** against cancer proteins and tumor-specific
**neoantigens** through molecular docking, ML response prediction, and an agent-based
tumor simulation — visualized in real time — and rank candidates as **research
hypotheses** that sharpen through a lab-result feedback loop.

> **It does not produce cures, and it says so everywhere.** Every output is a research
> hypothesis for laboratory investigation, not a treatment, cure, dose, or medical
> recommendation. A compound that shrinks cells in a model still needs cell-culture work,
> animal studies, and human clinical trials. The disclaimer is wired into the schema, the
> API, and every export — it cannot be turned off.

This repository implements **Part A** of the [design spec](docs/superpowers/specs/2026-06-19-naturascreen-design.md):
a runnable system. Part B (digital-twin trial simulation) is an explicitly speculative
roadmap and is **not** built.

---

## Two honesty boundaries, enforced by the type system

NaturaScreen makes two distinct claims that are easy to conflate, and both are enforced
structurally (not by convention):

1. **The cure boundary** (`DISCLAIMER`). Every results/report/export response inherits a
   Pydantic base whose `disclaimer` field defaults to the canonical text and is
   non-optional — it is always serialized. The frontend report component is typed to
   require it.
2. **The illustration boundary** (`SIMULATION_NOTICE`). The agent simulation is a
   *qualitative illustration of the effectiveness score, not a prediction of tumor
   response*. There is no validated function mapping a binding score (kcal/mol) to a tumor
   growth rate; that mapping lives in one named, documented function
   (`HeuristicEffectTransfer`) and is labelled illustrative. The notice rides on the
   websocket's mandatory opening envelope **and on every frame**, and the 3D viewer
   refuses to render cells without displaying it.

Both constants have a single source of truth in [`api/naturascreen/disclaimer.py`](api/naturascreen/disclaimer.py).

---

## Architecture

```
Next.js 15 (App Router, TS)            FastAPI (async)                 Celery worker
  compound browser                       /compounds /targets             experiment pipeline:
  neoantigen explorer        REST  ───►   /neoantigens /experiments  ──►   score → persist → simulate
  experiment builder         WS    ◄───   /feedback                       scheduled retrain (beat)
  live r3f tumor view  ◄── deterministic frame stream ──┘
  D3 population panel                    Postgres 16 · Redis (broker)
  candidate report (PDF/JSON)
```

The simulation streams over a websocket as a **deterministic re-run from the experiment's
seed** — race-free, replayable, and scrubber-friendly (a refinement over live Redis frame
pub/sub; see the spec).

## Scientific pipeline

| Stage | What it does | Tool | Status |
|---|---|---|---|
| Compound library | Natural products → SMILES + RDKit descriptors | COCONUT (CC0) REST + RDKit | **real, works immediately** |
| Docking | Binding affinity vs. a curated pocket box | AutoDock Vina + Meeko | real adapter (needs Vina + receptor) |
| Neoantigen | Peptide–MHC presentation %rank | MHCflurry | real adapter (needs `make data-mhcflurry`) |
| Response | Predicted cell-line ln(IC50) + OOD flag | XGBoost on GDSC1 | real adapter (needs `make data-response`) |
| Simulation | Agent-based tumor population (illustrative) | NumPy | **real mechanics, illustrative biology** |

**No fake fallbacks.** When a tool/dataset is not provisioned, that sub-score is reported
`unavailable` and excluded from scoring — never fabricated. `/meta` reports what is
actually provisioned.

### Scoring (exposed, auditable)

`effectiveness = Σ wᵢ · normalizedᵢ` over only the sub-scores actually computed. Each
sub-score is mapped to `[0,1]` via a **fixed, documented reference window** (not batch
min-max, not rank), so a compound's score doesn't change based on what else was screened.
Missing sub-scores are **excluded and the weights renormalized** — never imputed as 0. The
`simulation` term defaults to weight **0** (it's derived from the other sub-scores;
weighting it would double-count). The report exposes raw · window · normalized · weight ·
contribution per channel. See [`services/scoring`](api/naturascreen/services/scoring).

### Natural-compound transfer (honest OOD)

The response model is trained on synthetic-drug screens (GDSC) and is out-of-distribution
for most natural products. Each prediction carries an **applicability-domain flag**
(nearest-neighbour ECFP4 Tanimoto to the training set); OOD predictions are flagged
low-confidence and surfaced in the report.

---

## Quickstart (local Docker Compose)

```bash
cp .env.example .env
make up                 # postgres, redis, api, worker, beat, web
make migrate            # apply the schema
make ingest-compounds n=300   # pull natural products from COCONUT (live, CC0)
open http://localhost:3000
```

Try the **Simulator** page for the live illustrative tumor view, or build an experiment
under **Experiments** (pick compounds → run → ranked report with PDF/JSON export).

### Provisioning the real scientific adapters

```bash
make curate-targets     # load curated cancer targets with cited docking boxes
make data-response      # train the response model: needs a real GDSC1 CSV at /data (see train.py)
make data-mhcflurry     # fetch MHCflurry models (set WORKER_EXTRAS=docking,neoantigen,response first)
# docking also needs a prepared receptor PDBQT at /data/docking/receptors/<PDB_ID>.pdbqt
```

Until these run, the corresponding sub-scores report `unavailable` and the pipeline still
completes honestly (combined score from whatever is available).

---

## Tests

```bash
make test         # full backend suite, in-container (84 passing; Vina/MHCflurry-gated tests skip)
make test-core    # dependency-light core logic (sim, scoring, normalization, disclaimer, parsing)
cd web && npx tsc --noEmit   # frontend typecheck
```

Tests assert behaviour, not plumbing: simulation population dynamics under a seed, the
normalization windows + missing-subscore renormalization + circularity guard, the two
safety notices being structurally inescapable, COCONUT parsing against recorded rows, the
applicability-domain Tanimoto math, adapter `unavailable` gating, and the full experiment
flow + websocket protocol through the real ASGI app.

## Tech stack & attribution

- **Backend**: FastAPI, SQLAlchemy 2 (async) + asyncpg, Alembic, Celery + Redis, RDKit,
  AutoDock Vina + Meeko, MHCflurry, XGBoost + scikit-learn, reportlab.
- **Frontend**: Next.js 15, react-three-fiber + three, D3, Tailwind, zustand.
- **Data**: [COCONUT 2.0](https://coconut.naturalproducts.net) (CC0), GDSC1
  (cancerrxgene.org), RCSB PDB. Docking pocket boxes are hand-curated with literature
  citations in [`targets_registry.py`](api/naturascreen/services/docking/targets_registry.py).

## Repository layout

```
api/   FastAPI backend, Celery tasks, services (compounds, simulation, scoring, report,
       docking, neoantigen, response), Alembic migrations, tests/{core,integration}
web/   Next.js app (dashboard, compounds, targets, neoantigens, simulate, experiments)
docs/  design spec
```

## Ethics & safety (non-negotiable)

No treatment/cure/dose language. Every report and export embeds the disclaimer. Accuracy
and uncertainty are reported honestly (real CV numbers, OOD flags, docking noise). Sources
are cited. No patient data is stored. The simulation is always labelled illustrative.
Real validation requires lab and clinical work — stated on every results page.
