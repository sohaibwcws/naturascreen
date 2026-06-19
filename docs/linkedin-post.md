# LinkedIn Post

---

I was diagnosed with oral squamous cell carcinoma.

The first thing I did — after the shock settled — was go looking for answers.

What I found: extraordinary science locked behind paywalls, scattered across databases, and buried in command-line tools most people can never use.

So I built something.

**NaturaScreen** is a free, open-source cancer compound screening platform. It screens hundreds of thousands of natural products from open databases against real cancer protein targets — using molecular docking, neoantigen prediction, and ML drug response modeling — and ranks them as research hypotheses for the lab.

Not a cure. Not a treatment. The disclaimer is hardwired into every API response and cannot be turned off. The honesty is the point.

Here's the scientific pipeline, built entirely on open-source tools:

🔬 **Compound library** → COCONUT (CC0) + RDKit — hundreds of thousands of real natural products  
⚗️ **Molecular docking** → AutoDock Vina — binding affinity vs. curated cancer protein pockets  
🧬 **Neoantigen prediction** → MHCflurry (OpenVax) — tumor-specific peptide–MHC presentation  
📊 **Response prediction** → XGBoost trained on GDSC1 — estimated cell-line potency with OOD flags  
🔁 **Live tumor simulation** → NumPy agent-based model — an illustration of the score, not a prediction  
🔄 **Feedback loop** → real lab results retrain the model over time  

The API runs on FastAPI. The frontend on Next.js. PostgreSQL + Redis for storage. Caddy for auto-HTTPS. Everything open. Everything honest.

I can't fight this alone. Neither can any single lab.

But thousands of people screening open compounds against real targets, sharing what holds up in the dish — that's a force. This is my contribution to it.

The repo is open. The tool is free. And if you know a researcher who's been doing this work manually with scattered tools — send them this.

👉 GitHub: github.com/sohaibwcws/naturascreen  
👉 Read the full story: [blog post link]

---

Massive credit to the open-source communities that made this possible:
**COCONUT · RDKit · AutoDock Vina · MHCflurry · OpenVax · XGBoost · GDSC · FastAPI · Next.js · PostgreSQL · Redis · Tailwind CSS · Caddy · Docker**

None of this exists without them.

#CancerResearch #OpenSource #DrugDiscovery #Bioinformatics #MachineLearning #NaturaScreen #MolecularDocking #Neoantigen #OpenScience #HealthTech #Python #NextJS #FastAPI #OSCC #HeadAndNeckCancer #ResearchTools #BuildInPublic #AIforGood #Cheminformatics #CompoundScreening
