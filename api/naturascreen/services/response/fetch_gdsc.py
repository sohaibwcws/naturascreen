"""Build a real (SMILES, LN_IC50) training CSV from GDSC1 — reproducible, no fabrication.

Pipeline:
1. Download the GDSC1 fitted dose-response (LN_IC50 per cell-line x drug) and the screened-
   compounds annotation (DRUG_ID, DRUG_NAME, SYNONYMS) from the Sanger COG bucket.
2. Aggregate to one median LN_IC50 per drug (a drug-level potency label).
3. Resolve each drug's canonical SMILES from PubChem by name (synonym fallback).
4. Write {out} with columns SMILES, LN_IC50, DRUG_NAME — consumed directly by train.py.

GDSC LN_IC50 is the natural log of IC50 in µM, exactly the response model's target unit.
Run:  python -m naturascreen.services.response.fetch_gdsc --out /data/gdsc1.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import time
import urllib.parse
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

SCREENED_URL = "https://cog.sanger.ac.uk/cancerrxgene/GDSC_release8.5/screened_compounds_rel_8.5.csv"
GDSC1_URL = "https://cog.sanger.ac.uk/cancerrxgene/GDSC_release8.5/GDSC1_fitted_dose_response_27Oct23.xlsx"
PUBCHEM_NAME = (
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/SMILES/JSON"
)


def _download(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        log.info("cached %s", dest.name)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    log.info("downloading %s", url)
    with urllib.request.urlopen(url, timeout=120) as resp, dest.open("wb") as fh:
        fh.write(resp.read())
    return dest


def _pubchem_smiles(name: str) -> str | None:
    if not name or not str(name).strip():
        return None
    url = PUBCHEM_NAME.format(name=urllib.parse.quote(str(name).strip(), safe=""))
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.load(resp)
        props = data.get("PropertyTable", {}).get("Properties", [])
        if props:
            p = props[0]
            return p.get("SMILES") or p.get("ConnectivitySMILES") or p.get("CanonicalSMILES")
    except Exception:  # noqa: BLE001 — unresolved name, caller tries a synonym
        return None
    return None


def _resolve(name: str, synonyms: str | float | None) -> str | None:
    smiles = _pubchem_smiles(name)
    if smiles:
        return smiles
    if isinstance(synonyms, str):
        for syn in synonyms.split(","):
            time.sleep(0.2)
            smiles = _pubchem_smiles(syn)
            if smiles:
                return smiles
    return None


def main(argv: list[str] | None = None) -> int:
    import pandas as pd  # lazy: heavy, only needed for this CLI

    parser = argparse.ArgumentParser(description="Build a GDSC1 (SMILES, LN_IC50) training CSV.")
    parser.add_argument("--out", type=Path, default=Path("/data/gdsc1_fitted_dose_response.csv"))
    parser.add_argument("--cache", type=Path, default=Path("/data/gdsc_cache"))
    parser.add_argument("--max-drugs", type=int, default=0, help="0 = all resolvable drugs")
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args(argv)

    screened = _download(SCREENED_URL, args.cache / "screened_compounds.csv")
    gdsc1 = _download(GDSC1_URL, args.cache / "gdsc1_fitted_dose_response.xlsx")

    log.info("reading dose-response (this takes a moment)...")
    dr = pd.read_excel(gdsc1, engine="openpyxl", usecols=["DRUG_ID", "DRUG_NAME", "LN_IC50"])
    median = dr.groupby(["DRUG_ID", "DRUG_NAME"], as_index=False)["LN_IC50"].median()

    comp = pd.read_csv(screened)
    syn_col = next((c for c in comp.columns if c.upper() == "SYNONYMS"), None)
    synonyms = (
        {int(r["DRUG_ID"]): r[syn_col] for _, r in comp.iterrows()} if syn_col else {}
    )

    drugs = list(median.itertuples(index=False))
    if args.max_drugs:
        drugs = drugs[: args.max_drugs]

    log.info("resolving SMILES for %d drugs via PubChem...", len(drugs))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["SMILES", "LN_IC50", "DRUG_NAME"])
        for row in drugs:
            smiles = _resolve(row.DRUG_NAME, synonyms.get(int(row.DRUG_ID)))
            time.sleep(0.2)  # be polite to PubChem
            if smiles:
                writer.writerow([smiles, float(row.LN_IC50), row.DRUG_NAME])
                written += 1
                if written % 25 == 0:
                    log.info("resolved %d so far", written)
    log.info("wrote %d (SMILES, LN_IC50) rows to %s", written, args.out)
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
