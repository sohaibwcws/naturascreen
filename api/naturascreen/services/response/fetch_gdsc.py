"""Build a real per-(cell-line, drug) training CSV from GDSC1 — reproducible, no fabrication.

Pipeline:
1. Download GDSC1 fitted dose-response (LN_IC50 per cell-line × drug) and the screened-
   compounds annotation (DRUG_NAME, SYNONYMS) from the Sanger COG bucket.
2. Resolve each drug's canonical SMILES from PubChem by name (synonym fallback); cache the
   name→SMILES map so reruns are instant.
3. Emit one row per (cell line, drug): SMILES, CELL_LINE, TISSUE, LN_IC50.

Keeping the cell-line dimension (with its tissue) is what lets the response model learn the
genomic/context variance the PRD intended ("descriptors + cell-line genomics"), instead of
collapsing every drug to a single median. GDSC LN_IC50 is the natural log of IC50 in µM.

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


def _resolve_one(name: str, synonyms: str | float | None) -> str | None:
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


def _smiles_map(names: dict[str, str | float | None], cache: Path) -> dict[str, str]:
    """Resolve {drug_name: synonyms} -> {drug_name: SMILES}, cached to disk."""
    cache_file = cache / "smiles_map.json"
    if cache_file.exists():
        log.info("cached SMILES map")
        return json.loads(cache_file.read_text())
    resolved: dict[str, str] = {}
    for i, (name, syns) in enumerate(names.items(), 1):
        smiles = _resolve_one(name, syns)
        time.sleep(0.2)
        if smiles:
            resolved[name] = smiles
        if i % 25 == 0:
            log.info("resolved %d/%d drug names", len(resolved), i)
    cache.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(resolved))
    return resolved


def main(argv: list[str] | None = None) -> int:
    import pandas as pd  # lazy: heavy, only needed for this CLI

    parser = argparse.ArgumentParser(description="Build a GDSC1 per-(cell-line, drug) CSV.")
    parser.add_argument("--out", type=Path, default=Path("/data/gdsc1.csv"))
    parser.add_argument("--cache", type=Path, default=Path("/data/gdsc_cache"))
    parser.add_argument("--max-rows", type=int, default=120000, help="0 = all rows")
    parser.add_argument("--seed", type=int, default=0)
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args(argv)

    screened = _download(SCREENED_URL, args.cache / "screened_compounds.csv")
    gdsc1 = _download(GDSC1_URL, args.cache / "gdsc1_fitted_dose_response.xlsx")

    comp = pd.read_csv(screened)
    syn_col = next((c for c in comp.columns if c.upper() == "SYNONYMS"), None)
    name_syn = {
        str(r["DRUG_NAME"]): (r[syn_col] if syn_col else None) for _, r in comp.iterrows()
    }

    log.info("reading dose-response (this takes a moment)...")
    dr = pd.read_excel(
        gdsc1, engine="openpyxl", usecols=["DRUG_NAME", "CELL_LINE_NAME", "TCGA_DESC", "LN_IC50"]
    )
    # Resolve SMILES for the drug names actually present in the dose-response table.
    present = {str(n): name_syn.get(str(n)) for n in dr["DRUG_NAME"].dropna().unique()}
    smiles_map = _smiles_map(present, args.cache)
    log.info("resolved SMILES for %d/%d drugs", len(smiles_map), len(present))

    dr = dr[dr["DRUG_NAME"].astype(str).isin(smiles_map)].copy()
    if args.max_rows and len(dr) > args.max_rows:
        dr = dr.sample(n=args.max_rows, random_state=args.seed)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["SMILES", "CELL_LINE", "TISSUE", "LN_IC50"])
        for row in dr.itertuples(index=False):
            smiles = smiles_map.get(str(row.DRUG_NAME))
            tissue = str(row.TCGA_DESC) if isinstance(row.TCGA_DESC, str) and row.TCGA_DESC else "UNKNOWN"
            if smiles:
                writer.writerow([smiles, row.CELL_LINE_NAME, tissue, float(row.LN_IC50)])
                written += 1
    log.info("wrote %d (cell-line, drug) rows to %s", written, args.out)
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
