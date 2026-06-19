"""Train the response model on REAL GDSC1 data — NEVER on fabricated rows.

Input is the per-(cell-line, drug) CSV from ``fetch_gdsc`` with columns SMILES, TISSUE,
LN_IC50 (CELL_LINE optional/ignored). Features are the compound block (RDKit descriptors +
folded ECFP4) plus a tissue one-hot, so the model learns cell-line/tissue context rather
than collapsing a drug to one number.

Two cross-validation schemes are reported honestly:
- ``random``  — 5-fold over (compound, cell-line) rows: the model's skill at the IC50
  regression task. High here largely reflects learnable cell-line/tissue variance.
- ``leave_compounds_out`` — GroupKFold grouped by compound: the HONEST screening metric,
  i.e. how well it generalizes to a compound it has never seen (the actual use case for
  natural-product screening). This is the number that matters for ranking new compounds.

Canonical source: GDSC1 fitted dose response — https://www.cancerrxgene.org/downloads/bulk_download
Run:  python -m naturascreen.services.response.train --csv /data/gdsc1.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

from ...config import get_settings
from ..compounds.descriptors import FEATURE_KEYS
from . import model as model_store
from .features import feature_vector

log = logging.getLogger(__name__)

GDSC1_SOURCE = "GDSC1 fitted dose response — https://www.cancerrxgene.org/downloads/bulk_download"
DEFAULT_CSV_NAME = "gdsc1.csv"

_SMILES_CANDIDATES = ("SMILES", "smiles", "canonical_smiles", "CanonicalSMILES")
_LN_IC50_CANDIDATES = ("LN_IC50", "ln_ic50", "LnIC50")
_IC50_UM_CANDIDATES = ("IC50_uM", "IC50", "ic50")
_TISSUE_CANDIDATES = ("TISSUE", "tissue", "TCGA_DESC")


class TrainingDataError(SystemExit):
    """Raised (as a clean non-zero exit) when real data is missing or unusable."""

    def __init__(self, message: str):
        super().__init__(f"error: {message}")


def _pick(columns, candidates, what, required=True):
    for c in candidates:
        if c in columns:
            return c
    if required:
        raise TrainingDataError(f"CSV has no {what} column (looked for {candidates}); got {columns}")
    return None


def _load_rows(path: Path) -> tuple[list[str], list[str], list[float]]:
    """Read (smiles, tissue, ln_ic50) lists from a real CSV. Tissue defaults to UNKNOWN."""
    import math

    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        cols = reader.fieldnames or []
        scol = _pick(cols, _SMILES_CANDIDATES, "SMILES")
        lcol = _pick(cols, _LN_IC50_CANDIDATES, "LN_IC50", required=False)
        icol = None if lcol else _pick(cols, _IC50_UM_CANDIDATES, "IC50")
        tcol = _pick(cols, _TISSUE_CANDIDATES, "TISSUE", required=False)
        smiles_out: list[str] = []
        tissue_out: list[str] = []
        y_out: list[float] = []
        for row in reader:
            smiles = (row.get(scol) or "").strip()
            if not smiles:
                continue
            if lcol and row.get(lcol):
                ln = float(row[lcol])
            elif icol and row.get(icol):
                ic50 = float(row[icol])
                if ic50 <= 0:
                    continue
                ln = math.log(ic50)
            else:
                continue
            smiles_out.append(smiles)
            tissue_out.append((row.get(tcol) or "UNKNOWN").strip() if tcol else "UNKNOWN")
            y_out.append(ln)
    if not smiles_out:
        raise TrainingDataError(f"no usable rows in {path}")
    return smiles_out, tissue_out, y_out


def _xgb_regressor(seed: int):
    import xgboost as xgb

    return xgb.XGBRegressor(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.7,
        random_state=seed,
        n_jobs=0,
    )


def _cv(X, y, groups, folds: int, seed: int) -> dict:
    import numpy as np
    from sklearn.metrics import mean_squared_error, r2_score
    from sklearn.model_selection import GroupKFold, KFold

    X = np.asarray(X)
    y = np.asarray(y)
    groups = np.asarray(groups)

    def _score(splitter, split_args) -> dict:
        oof = np.full(len(y), np.nan)
        for train_idx, test_idx in splitter.split(*split_args):
            reg = _xgb_regressor(seed)
            reg.fit(X[train_idx], y[train_idx])
            oof[test_idx] = reg.predict(X[test_idx])
        mask = ~np.isnan(oof)
        return {
            "r2": round(float(r2_score(y[mask], oof[mask])), 4),
            "rmse": round(float(mean_squared_error(y[mask], oof[mask]) ** 0.5), 4),
            "n": int(mask.sum()),
        }

    k = min(folds, max(2, len(set(groups.tolist()))))
    return {
        "random": {**_score(KFold(n_splits=folds, shuffle=True, random_state=seed), (X, y)), "scheme": "5-fold over (compound,cell-line) rows"},
        "leave_compounds_out": {**_score(GroupKFold(n_splits=k), (X, y, groups)), "scheme": "GroupKFold grouped by compound — generalization to unseen compounds"},
    }


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Train the response model on real GDSC1 data.")
    parser.add_argument("--csv", type=Path, default=Path(settings.data_dir) / DEFAULT_CSV_NAME)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--artifacts", type=Path, default=None)
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args(argv)

    # Refuse to run on absent data BEFORE importing the heavy stack — never fabricate.
    if not args.csv.is_file():
        raise TrainingDataError(
            f"GDSC1 CSV not found at {args.csv}. Run `python -m naturascreen.services.response."
            f"fetch_gdsc --out {args.csv}` first. Will not fabricate data."
        )

    smiles, tissues, y = _load_rows(args.csv)

    from ..compounds.descriptors import compute

    # Descriptors per unique compound (cached); drop ones RDKit rejects.
    desc_cache: dict[str, dict | None] = {}
    for s in set(smiles):
        result = compute(s)
        desc_cache[s] = result[1] if result else None

    tissue_vocab = sorted(set(tissues))
    X, Y, groups = [], [], []
    onbits_by_smiles: dict[str, list[int]] = {}
    for s, t, target in zip(smiles, tissues, y):
        desc = desc_cache.get(s)
        if desc is None:
            continue
        X.append(feature_vector(desc, t, tissue_vocab))
        Y.append(target)
        groups.append(s)
        onbits_by_smiles.setdefault(s, list(desc.get("ecfp4_onbits") or []))

    n_compounds = len(onbits_by_smiles)
    log.info("training rows=%d, unique compounds=%d, tissues=%d", len(X), n_compounds, len(tissue_vocab))
    if n_compounds < args.folds:
        raise TrainingDataError(f"only {n_compounds} usable compounds; need >= {args.folds}")

    metrics = _cv(X, Y, groups, args.folds, args.seed)
    reg = _xgb_regressor(args.seed)
    reg.fit(X, Y)  # final model on all rows

    meta = model_store.ResponseMeta(
        feature_keys=list(FEATURE_KEYS),
        training_onbits=list(onbits_by_smiles.values()),
        cv_metric=metrics,
        source=GDSC1_SOURCE,
        tissue_vocab=tissue_vocab,
        extra={"rows": len(X), "compounds": n_compounds},
    )
    model_store.save(reg, meta, args.artifacts)

    rnd, lco = metrics["random"], metrics["leave_compounds_out"]
    print(f"Source: {GDSC1_SOURCE}")
    print(f"Rows={len(X)}  unique compounds={n_compounds}  tissues={len(tissue_vocab)}")
    print(f"CV random              R²={rnd['r2']:+.4f}  RMSE={rnd['rmse']:.4f}  (IC50 regression skill)")
    print(f"CV leave-compounds-out R²={lco['r2']:+.4f}  RMSE={lco['rmse']:.4f}  (HONEST: ranking unseen compounds)")
    print(f"Saved -> {model_store.model_path(args.artifacts)}")
    print("Set RESPONSE_MODEL_READY=1 to activate the adapter.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
