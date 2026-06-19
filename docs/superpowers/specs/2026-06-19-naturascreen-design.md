# NaturaScreen — Design Spec (Part A vertical slice)

Date: 2026-06-19
Owner: Sohaib Khan
Status: Approved with scientific-honesty + normalization revisions

## 0. What this is

NaturaScreen screens open-source natural compounds against cancer targets and ranks
them as **research hypotheses**, with a real-time agent-based tumor visualization.
It produces candidate hypotheses for lab investigation. It does **not** produce a
verified cure, a treatment, a dose, or a patient prediction. Every result and export
carries a disclaimer enforced by the type system.

This spec covers **Part A** only. Part B (digital twin, quantum layer, organoid loop)
is explicitly out of scope — speculative roadmap, not built.

## 1. Scope of this slice

Fully real and demoable day one (no external data needed):
- Agent-based tumor **simulation engine** (mechanics) + live WebSocket frame stream.
- Custom **react-three-fiber** 3D tumor view + D3 population panel.
- **Scoring** service (normalization + weighting, exposed) and **candidate report**.
- **Disclaimer** + **simulation illustrative-notice**, both type-enforced.
- Data model + migrations.
- **Compound library** ingestion from COCONUT (public CC0 REST API — real immediately).

Real adapters, layered after the spine (run real tools in Linux containers; need
binaries/data fetched via documented `make` targets; **never fake fallbacks** — when
unavailable the API returns an explicit `unavailable` status, never a fabricated number):
- **Docking**: AutoDock Vina (pip bindings) + RDKit/Meeko prep.
- **Neoantigen**: MHCflurry (open, no license gate).
- **Response ML**: XGBoost on a real public GDSC1 subset.

## 2. Architecture

- **Frontend**: Next.js 15 (App Router, TS) — compound browser, neoantigen explorer,
  experiment builder, live visualizer, results dashboard, candidate report. Tailwind,
  zustand, react-three-fiber + drei, d3. Dark scientific theme. WCWS footer in root layout.
- **Backend**: FastAPI (async), SQLAlchemy 2.0 async + asyncpg, Alembic, pydantic v2,
  Celery + Redis. REST + WebSocket.
- **Worker**: Celery — runs the pipeline; simulation publishes frames to Redis pub/sub;
  WS streamer relays to browser.
- **Infra**: docker-compose — postgres:16, redis:7, api, worker, web. Local dev-first.

Data flow (experiment run): `POST /experiments` → `POST /experiments/{id}/run`
(enqueue) → worker: docking → response → simulation(top compounds) → scoring → report;
simulation publishes frames to `exp:{id}:frames`; `WS /experiments/{id}/stream` relays.

## 3. SCIENTIFIC HONESTY (load-bearing — read before writing sim code)

The agent simulation is the most scientifically arbitrary part of the system. There is
**no validated function** mapping a Vina binding score (kcal/mol) or a predicted IC50 to
a tumor growth/death rate. That mapping is invented. A smooth real-time tumor shrinking
on screen looks authoritative and is not a prediction.

Rules:
1. The "fully real" claim applies to **engine mechanics only** (agent dynamics, numerical
   integration, frame streaming) — never to the biology the animation implies.
2. The score→rate mapping is a single named function `HeuristicEffectTransfer`,
   documented as illustrative, with parameters exposed in the UI. It is not presented as
   a model of tumor response.
3. A second notice, as load-bearing as the cure disclaimer, is **type-enforced**:
   - Constant `SIMULATION_NOTICE` (single source of truth).
   - Non-optional `illustrative_notice: str` on `SimulationRun`, **every frame payload**,
     results, and report DTOs.
   - The r3f viewer cannot render a frame without persistently overlaying it.
   - Text: "Qualitative illustration of the effectiveness score, not a prediction of
     tumor response. The shrinkage rate shown is a heuristic transfer from the compound's
     scores, not a validated model of any real tumor or patient."

## 4. SCORING + NORMALIZATION (first-class — the core scientific decision)

Combined score: `effectiveness = Σ wᵢ · normalizedᵢ` over **only the sub-scores actually
computed**. Weights are configurable and surfaced in the UI and report.

### 4.1 Normalization method: fixed documented reference windows
Chosen over batch min-max (a compound's score must not change based on what else was in
the batch) and over rank/quantile (discards magnitude). Each sub-score: clamp to a stated
window → monotonic map to [0,1], higher = better. All windows are configurable constants
with cited rationale, exposed per-compound in the report.

| Sub-score | Native unit | Window (→1 .. →0) | Rationale / flags |
|---|---|---|---|
| Binding | kcal/mol (Vina) | −12 .. −6 | weaker than −6 = non-specific floor; box-dependent; noisy |
| Neoantigen | MHCflurry presentation %rank | 0.0 .. 2.0 | %rank is allele-normalized; gated by target-is-neoantigen match |
| Response | ln(IC50 µM) | ln(0.01) .. ln(100) | lower IC50 = better; down-weighted/flagged when OOD (§5) |
| Simulation | reduction fraction [0,1] | 1.0 .. 0.0 | illustrative; default weight 0 (§4.3) |

### 4.2 Missing sub-scores
Exclude and **renormalize weights over what was computed**. Never impute a missing
sub-score as 0 (that punishes "not measured" as "no effect"). The report states exactly
which sub-scores fed the rank and which were absent and why.

### 4.3 Circularity guard
The simulation's reduction is driven by binding+response, so feeding it back as an
independent term double-counts. Therefore `w4` (simulation term) **defaults to 0**. If a
user raises it, the report prints a warning that the term is derived from binding+response
and double-counts. PRD §4's four-term formula stays configurable for fidelity; the default
refuses to let the illustration inflate the ranking.

### 4.4 Auditability
Per compound, the report exposes: raw value · window used · normalized value · weight ·
contribution. Ranking is fully traceable, never a black box.

## 5. Natural-compound transfer (response model honesty)

XGBoost trained on GDSC (synthetic drugs) is out-of-distribution for most natural products.
GDSC cross-validation says nothing about a turmeric metabolite. Therefore:
- Report GDSC CV metrics honestly (real number, no inflation).
- Per-prediction **applicability-domain flag**: nearest-neighbor Tanimoto (ECFP4) to the
  training set; below threshold → prediction flagged **OOD / low-confidence**, and
  (configurably) down-weighted or excluded from the rank.
- Where a natural-product-labeled subset exists (e.g. NCI-60 NP screens), report that
  metric too.
- The report states plainly: the response model is trained on synthetic-drug data and is
  OOD for most natural products.

## 6. Docking box curation (not a bake step)

Defining the search box per protein is human curation work that determines whether scores
mean anything. `targets` gains `box_center_{x,y,z}` + `box_size_{x,y,z}`. A target is not
`dockable` until a human records its pocket box with a cited source. Ship a few
hand-curated targets with box provenance. The report shows the box used. Absent/wrong box
→ target marked not-dockable, no score emitted (never a fabricated score).

## 7. Disclaimer enforcement (PRD §14)

Single `DISCLAIMER` constant → non-optional `disclaimer: str` on every results/report
model → frontend report component typed to require it (empty-states without it) → PDF/JSON
embed it in the document body → permanent banner on results pages. Enforced by the type
system, zero exceptions.

## 8. Data model (PRD §10, verbatim + curation additions)

SQLAlchemy 2.0 models + Alembic migration:
`compounds, targets (+ box fields, dockable flag), neoantigens, experiments,
docking_results (+ box used), response_predictions (+ applicability-domain flag),
simulation_runs (+ illustrative_notice), effectiveness_scores (raw/window/normalized/
weight/contribution per sub-score), lab_results`.

## 9. API (PRD §9) — every results/report response carries `disclaimer`; every
simulation/results/report response carries `illustrative_notice`.

`GET /compounds`, `GET /targets`, `POST /neoantigens/predict`, `POST /experiments`,
`POST /experiments/{id}/run`, `GET /experiments/{id}/results`,
`WS /experiments/{id}/stream`, `GET /experiments/{id}/report`, `POST /feedback/lab-result`.

## 10. Testing (behavior, not plumbing)

pytest: sim population dynamics under seeded known rates (deterministic); normalization
math (window clamp, monotonicity, missing-subscore renormalization, w4=0 default);
disclaimer + illustrative_notice present in every relevant DTO; COCONUT parse against a
recorded fixture; applicability-domain flag triggers on a far compound; experiment state
machine. Frontend: report refuses to render without disclaimer; viewer overlays notice on
frames; WS frame parser. Real E2E smoke: compose up → ingest compounds → run sim
experiment → observe live frames (with notice) → fetch report (with disclaimer).

## 11. Build order

Spine built sequentially (one agent — sim/score/frame-format/viz are tightly coupled;
get frames flowing end-to-end once before fanning out):
1. Foundation: repo, compose, models, migrations, config, `disclaimer.py`, `SIMULATION_NOTICE`, health.
2. Compound library: COCONUT ingest (API + bulk CSV) + search API + Next.js browser.
3. Spine: agent engine + `HeuristicEffectTransfer` + score schema/normalization + frame
   format + Redis pub/sub + Celery task + WS streamer + r3f tumor view + D3 panel +
   experiment builder/run UI. **Frames flow end-to-end with notice overlaid.**
4. Scoring + report: scoring service (§4), candidate report, JSON/PDF export, results dashboard.

Then parallelize the genuinely-independent adapters (subagents):
5a. Vina docking adapter + target box curation + UI.
5b. MHCflurry neoantigen adapter + mutant-peptide/HLA input + explorer UI.
5c. XGBoost response model (train script + bundled checkpoint + applicability-domain) + wire-in.

Then:
6. Feedback: `POST /feedback/lab-result` + scheduled retrain task.
7. Polish: README, example experiment, `make data` scripts, caching, tests green.

## 12. Stack pins

Backend: Python 3.12, FastAPI, SQLAlchemy 2 async, asyncpg, Alembic, pydantic v2 +
pydantic-settings, Celery, redis, RDKit, vina, meeko, mhcflurry, xgboost, numpy, reportlab.
Frontend: Next.js 15, react, react-three-fiber, @react-three/drei, three, d3, zustand,
tailwindcss. Infra: docker-compose (postgres:16, redis:7).
