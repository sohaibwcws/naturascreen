# I Was Diagnosed with Cancer. So I Built an Open-Source Drug Screening Platform.

*By Sohaib Khan*

---

## The Day Everything Changed

I'm Sohaib Khan. A few months ago, I was diagnosed with oral squamous cell carcinoma — OSCC, a form of head and neck cancer. Hearing those words doesn't just change your prognosis. It changes the way you read. The way you search. The questions you ask at 2 a.m.

I went looking for answers the only way I know how: through code, data, and obsessive reading. What I found shook me.

The science is extraordinary. Researchers around the world are doing breathtaking work — mapping tumor neoantigens, screening thousands of compounds against cancer proteins, building predictive models of cell-line drug response. The problem is that almost none of it is accessible. It lives behind paywalls. In scattered databases. In command-line tools that require a PhD just to install.

I couldn't fight my diagnosis alone. But I could build something.

---

## What Is NaturaScreen?

**NaturaScreen** is a free, open-source platform that puts real molecular compound screening, neoantigen prediction, and tumor simulation into a single tool anyone can run — researchers, students, curious builders, or patients who won't stop asking "what if?"

It is not a cure. It doesn't claim to be. That disclaimer is wired into the code itself — it ships in every API response, every export, every rendered report. It cannot be turned off. The honesty is the point.

What it *is*: a research hypothesis engine. A way to ask, faster and more rigorously, "does this natural compound deserve a closer look against this cancer target?"

---

## How It Works: The Scientific Pipeline

### Compound Library — COCONUT + RDKit

NaturaScreen starts with **COCONUT**, one of the largest open databases of natural products, licensed CC0. Hundreds of thousands of real compounds — plant alkaloids, fungal metabolites, marine secondary metabolites — each parsed into SMILES strings and molecular descriptors via **RDKit**.

This is the search space. Nature's library. Most of it has never been screened against most tumors.

### Molecular Docking — AutoDock Vina

For each candidate compound, NaturaScreen uses **AutoDock Vina** to estimate how strongly it binds to a curated cancer protein target. The docking boxes — the 3D coordinate regions where a drug molecule must fit to have effect — are hand-curated with citations. No fabricated geometry.

Vina runs on Linux via Docker or any host with the binary on PATH. When it isn't provisioned, the adapter reports `unavailable`. Never a fake number.

### Neoantigen Prediction — MHCflurry

Tumors mutate. Those mutations create peptides — neoantigens — that can be presented on the cell surface and recognized by the immune system. **MHCflurry** predicts which peptides bind which MHC alleles with what affinity.

This is the foundation of personalized cancer vaccines. NaturaScreen makes it explorable.

### Drug Response Prediction — XGBoost on GDSC1

The platform trains an **XGBoost** model on real data from the **Genomics of Drug Sensitivity in Cancer (GDSC)** dataset — thousands of drug–cell-line pairs with measured IC50 values. It predicts how potent a compound might be, including an honest out-of-distribution (OOD) flag for when the compound falls outside the training distribution. Most natural products do. We say so.

### Live Tumor Simulation — NumPy

The final step is an agent-based simulation — hundreds of virtual tumor cells responding in real time to a compound's estimated effectiveness score. It's an illustration, not a prediction. The notice is mandatory on every frame. But watching cells respond gives researchers an intuitive grip on the score before they ever touch a pipette.

### Feedback Loop — Lab Results Retrain the Model

Real assay results from the lab flow back into NaturaScreen and retrain the response model. The ranking gets sharper as real data arrives. This is how open science compounds.

---

## The Honest Design Philosophy

Every design choice in NaturaScreen enforces honesty:

- **No sub-score imputation.** If docking isn't available, it's excluded from the composite score — not counted as zero. Weights are renormalized over what's actually computed.
- **OOD flagging.** The XGBoost model knows it's out of distribution for natural products and says so, per prediction.
- **Two hard honesty boundaries enforced by the type system.** The `DISCLAIMER` field is non-optional in every Pydantic schema. The `SIMULATION_NOTICE` rides on every WebSocket frame. The frontend refuses to render without them.

This isn't just ethical. It's how you build tools researchers can actually trust.

---

## The Open-Source Stack

NaturaScreen is built entirely on open tools — no proprietary lock-in, no paywalls:

| Layer | Technology |
|---|---|
| Compound database | [COCONUT](https://coconut.naturalproducts.net/) (CC0) |
| Cheminformatics | [RDKit](https://www.rdkit.org/) |
| Molecular docking | [AutoDock Vina](https://vina.scripps.edu/) + [Meeko](https://github.com/forlilab/Meeko) |
| Neoantigen prediction | [MHCflurry](https://github.com/openvax/mhcflurry) (OpenVax) |
| Response ML | [XGBoost](https://xgboost.ai/) trained on [GDSC1](https://www.cancerrxgene.org/) |
| Agent simulation | [NumPy](https://numpy.org/) |
| API | [FastAPI](https://fastapi.tiangolo.com/) + [SQLAlchemy](https://www.sqlalchemy.org/) + [Alembic](https://alembic.sqlalchemy.org/) |
| Rate limiting | [slowapi](https://github.com/laurents/slowapi) |
| Frontend | [Next.js](https://nextjs.org/) + [Tailwind CSS](https://tailwindcss.com/) |
| Database | [PostgreSQL](https://www.postgresql.org/) + [Redis](https://redis.io/) |
| Reverse proxy | [Caddy](https://caddyserver.com/) (auto-HTTPS) |
| Containers | [Docker](https://www.docker.com/) + Compose |

Every one of these projects is maintained by communities of people who believe software should be open. NaturaScreen stands on their shoulders.

---

## Why This Matters Beyond My Own Diagnosis

Cancer kills roughly 10 million people every year. The research pipeline — from candidate molecule to approved drug — takes over a decade and costs billions of dollars. Most candidates fail. The search space of natural compounds is enormous and largely unexplored.

Tools that lower the cost of asking "what if?" don't replace clinical trials. They improve the odds that the candidate *reaching* a trial is the right one.

Thousands of researchers, students, and citizen scientists screening open compounds against real targets, sharing what holds up in the dish — that's a force. NaturaScreen is my contribution to that force.

---

## Run It Yourself

It's open source. The whole stack runs locally with Docker:

```bash
git clone <repo> && cd ssc-cancer
cp .env.example .env
make up
make migrate
make ingest-compounds n=300
open http://localhost:3000
```

No Docker? A no-service local run with SQLite works too.

---

## How You Can Help

**You don't have to be an oncologist to contribute to cancer research.**

- ★ **Star and share the repository** — reach is how open science compounds.
- ⚙ **Contribute** — better models, curated targets, validated lab results, new datasets.
- 🔬 **Bring real data** — if you run assays, submit results so the model learns what holds up in the dish.
- 📣 **Tell a researcher** who could put it to work.

The path from a computer simulation to a human life saved is long, hard, and full of necessary rigor. But every candidate that reaches a clinical trial had to start somewhere.

This is where some of them start now.

---

*NaturaScreen is free and open source. Nothing it produces is a treatment, cure, dose, or medical advice. If you or someone you love is facing cancer, please work with qualified clinicians.*

*— Sohaib Khan | [sohaib.com](https://sohaib.com)*
