"""Train the response model on REAL public GDSC1 data — NEVER on fabricated rows.

Canonical data source (download manually; the file is never committed):

    Genomics of Drug Sensitivity in Cancer — GDSC1, *fitted dose-response* export
    https://www.cancerrxgene.org/downloads/bulk_download

The GDSC1 fitted file reports ``LN_IC50`` (the natural log of the IC50 in µM) for each
(cell line, drug) pair, alongside ``DRUG_NAME``. It does NOT ship structures, so the export
must be augmented with a SMILES column (drug-name → SMILES resolved upstream from e.g.
PubChem/ChEMBL). This trainer refuses to run without SMILES and a target column rather than
inventing either — fabricating training data is the one thing the whole project forbids.

What this script does, honestly:
- Aggregates the (cell line, drug) rows to ONE ln(IC50) per unique compound (median across
  cell lines), because the model's features are compound-only descriptors and the adapter
  persists a single ``cell_line='aggregate'`` prediction. Aggregating per compound also makes
  the k-fold CV a genuine compound-level generalization estimate (no leakage of the same
  drug across folds).
- Computes RDKit descriptors via ``compounds.descriptors.compute`` and projects them through
  the shared ``features.feature_vector`` order.
- Fits an XGBoost regressor and runs k-fold CV, PRINTING the honest R²/RMSE (including poor
  values). GDSC is a screen of *synthetic* drugs, so the model is out-of-distribution for
  most natural products; when a natural-product label column is supplied, its subset metric
  is reported separately as a reminder of that bias.
- Saves the model (``response_model.ubj``) plus a meta sidecar (``response_meta.json``)
  carrying the training ECFP4 on-bits (for the applicability domain), the CV metric, the
  feature order, and provenance.

Usage (invoked by ``make data-response``):
    python -m naturascreen.services.response.train [--csv PATH] [--smiles-col COL]
        [--target-col COL] [--target-kind ln_ic50|ic50_um] [--np-col COL]
        [--folds K] [--seed N] [--artifacts DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ...config import get_settings
from ..compounds.descriptors import FEATURE_KEYS, compute
from . import model
from .features import feature_vector

GDSC1_SOURCE = "https://www.cancerrxgene.org/downloads/bulk_download"
DEFAULT_CSV_NAME = "gdsc1_fitted_dose_response.csv"

# Column-name candidates we auto-detect when not explicitly told. Real GDSC1 exports use
# LN_IC50 / DRUG_NAME; SMILES must be joined in upstream, so we accept the common spellings.
_SMILES_CANDIDATES = ("SMILES", "smiles", "Smiles", "canonical_smiles", "CanonicalSMILES")
_LN_IC50_CANDIDATES = ("LN_IC50", "ln_ic50", "LnIC50")
_IC50_UM_CANDIDATES = ("IC50_uM", "IC50_um", "IC50", "ic50_um", "ic50")


class TrainingDataError(SystemExit):
    """Raised (as a clean non-zero exit) when real data is missing or unusable."""

    def __init__(self, message: str) -> None:
        super().__init__(f"error: {message}")


def _pick_column(columns, explicit, candidates, what: str) -> str:
    if explicit:
        if explicit not in columns:
            raise TrainingDataError(f"--{what} column {explicit!r} not found in CSV")
        return explicit
    for cand in candidates:
        if cand in columns:
            return cand
    raise TrainingDataError(
        f"could not find a {what} column (looked for {', '.join(candidates)}); "
        f"pass it explicitly"
    )


def _build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    default_csv = str(Path(settings.data_dir) / DEFAULT_CSV_NAME)
    p = argparse.ArgumentParser(
        prog="python -m naturascreen.services.response.train",
        description=f"Train the response model on real GDSC1 data ({GDSC1_SOURCE}).",
    )
    p.add_argument("--csv", default=default_csv, help=f"GDSC1 fitted export (default {default_csv})")
    p.add_argument("--smiles-col", default=None, help="SMILES column name (auto-detected if omitted)")
    p.add_argument("--target-col", default=None, help="target column name (auto-detected if omitted)")
    p.add_argument(
        "--target-kind",
        choices=("ln_ic50", "ic50_um"),
        default=None,
        help="how to read the target: ln_ic50 (GDSC LN_IC50, used as-is) or ic50_um (µM, log-transformed)",
    )
    p.add_argument("--np-col", default=None, help="boolean/flag column marking natural-product rows")
    p.add_argument("--folds", type=int, default=5, help="k-fold CV splits (default 5)")
    p.add_argument("--seed", type=int, default=0, help="random seed (default 0)")
    p.add_argument("--artifacts", default=None, help="override artifacts output dir (testing)")
    return p


def _load_rows(args) -> tuple[list[str], list[float], list[bool]]:
    """Read and validate the CSV -> aligned (smiles, ln_ic50, is_np) row lists. Real data only."""
    import math

    # Guard for real data BEFORE importing pandas, so the "no data" refusal is clean even in a
    # minimal environment. Fabricating training data is the one thing the project forbids.
    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise TrainingDataError(
            f"GDSC1 CSV not found at {csv_path}. Download the GDSC1 fitted dose-response "
            f"export from {GDSC1_SOURCE}, join a SMILES column, and pass it via --csv. "
            f"This trainer will not fabricate data."
        )

    import pandas as pd

    frame = pd.read_csv(csv_path)
    if frame.empty:
        raise TrainingDataError(f"CSV {csv_path} has no rows")

    columns = list(frame.columns)
    smiles_col = _pick_column(columns, args.smiles_col, _SMILES_CANDIDATES, "smiles-col")

    # Resolve target column + kind. Prefer the native GDSC LN_IC50 (already ln(IC50 µM)).
    kind = args.target_kind
    if args.target_col:
        target_col = _pick_column(columns, args.target_col, (), "target-col")
        if kind is None:
            kind = "ln_ic50" if target_col in _LN_IC50_CANDIDATES else "ic50_um"
    elif kind == "ic50_um":
        target_col = _pick_column(columns, None, _IC50_UM_CANDIDATES, "target-col")
    elif kind == "ln_ic50":
        target_col = _pick_column(columns, None, _LN_IC50_CANDIDATES, "target-col")
    else:  # auto: LN_IC50 wins, else fall back to an IC50 (µM) column
        ln_match = next((c for c in _LN_IC50_CANDIDATES if c in columns), None)
        if ln_match:
            target_col, kind = ln_match, "ln_ic50"
        else:
            target_col = _pick_column(columns, None, _IC50_UM_CANDIDATES, "target-col")
            kind = "ic50_um"

    smiles_out: list[str] = []
    target_out: list[float] = []
    np_out: list[bool] = []
    for _, row in frame.iterrows():
        smiles = row.get(smiles_col)
        raw = row.get(target_col)
        if not isinstance(smiles, str) or not smiles.strip():
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if math.isnan(value) or math.isinf(value):
            continue
        ln_ic50 = value if kind == "ln_ic50" else math.log(value)
        if not math.isfinite(ln_ic50):
            continue
        smiles_out.append(smiles.strip())
        target_out.append(ln_ic50)
        np_out.append(bool(row.get(args.np_col)) if args.np_col else False)

    if not smiles_out:
        raise TrainingDataError(
            f"no usable (SMILES, {target_col}) rows in {csv_path} after validation"
        )
    return smiles_out, target_out, np_out


def _aggregate_by_compound(
    smiles: list[str], targets: list[float], is_np: list[bool]
) -> tuple[list[str], list[float], list[bool]]:
    """Median ln(IC50) per unique SMILES; NP flag = any row for that compound was flagged."""
    import statistics

    buckets: dict[str, dict] = {}
    for s, t, n in zip(smiles, targets, is_np):
        b = buckets.setdefault(s, {"targets": [], "np": False})
        b["targets"].append(t)
        b["np"] = b["np"] or n
    uniq_smiles = list(buckets)
    uniq_targets = [statistics.median(buckets[s]["targets"]) for s in uniq_smiles]
    uniq_np = [buckets[s]["np"] for s in uniq_smiles]
    return uniq_smiles, uniq_targets, uniq_np


def _featurize(
    smiles: list[str], targets: list[float], is_np: list[bool]
) -> tuple[list[list[float]], list[float], list[list[int]], list[bool], int]:
    """Compute descriptors per compound; drop ones RDKit rejects. Returns X, y, onbits, np, n_dropped."""
    X: list[list[float]] = []
    y: list[float] = []
    onbits: list[list[int]] = []
    np_flags: list[bool] = []
    dropped = 0
    for s, t, n in zip(smiles, targets, is_np):
        result = compute(s)
        if result is None:
            dropped += 1
            continue
        _, descriptors = result
        X.append(feature_vector(descriptors))
        y.append(t)
        onbits.append(list(descriptors.get("ecfp4_onbits") or []))
        np_flags.append(n)
    return X, y, onbits, np_flags, dropped


def _xgb_regressor(seed: int):
    import xgboost as xgb

    # Modest, untuned defaults — honest about being a baseline, not a leaderboard model.
    return xgb.XGBRegressor(
        n_estimators=400,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        random_state=seed,
        n_jobs=0,
        objective="reg:squarederror",
    )


def _cross_validate(X, y, folds: int, seed: int) -> tuple[list[float], dict]:
    """Pooled out-of-fold CV. Returns (oof_predictions, {r2, rmse, folds, n})."""
    import numpy as np
    from sklearn.metrics import mean_squared_error, r2_score
    from sklearn.model_selection import KFold

    Xa = np.asarray(X, dtype=float)
    ya = np.asarray(y, dtype=float)
    n = len(ya)
    k = max(2, min(folds, n))
    oof = np.zeros(n, dtype=float)
    kf = KFold(n_splits=k, shuffle=True, random_state=seed)
    for train_idx, test_idx in kf.split(Xa):
        reg = _xgb_regressor(seed)
        reg.fit(Xa[train_idx], ya[train_idx])
        oof[test_idx] = reg.predict(Xa[test_idx])
    rmse = float(np.sqrt(mean_squared_error(ya, oof)))
    r2 = float(r2_score(ya, oof))
    return oof.tolist(), {"r2": round(r2, 4), "rmse": round(rmse, 4), "folds": k, "n": n}


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    smiles, targets, is_np = _load_rows(args)
    smiles, targets, is_np = _aggregate_by_compound(smiles, targets, is_np)
    X, y, onbits, np_flags, dropped = _featurize(smiles, targets, is_np)

    if len(y) < 2:
        raise TrainingDataError(
            f"only {len(y)} usable compound(s) after descriptor computation "
            f"({dropped} rejected by RDKit); need at least 2 to train"
        )

    print(f"Loaded {len(y)} unique compounds ({dropped} rejected by RDKit) from {args.csv}")
    print(f"Source: GDSC1 fitted dose response — {GDSC1_SOURCE}")

    oof, cv_metric = _cross_validate(X, y, args.folds, args.seed)
    print(
        f"Cross-validated (k={cv_metric['folds']}, n={cv_metric['n']}) "
        f"R²={cv_metric['r2']}  RMSE={cv_metric['rmse']} (ln IC50 µM units)"
    )

    import numpy as np

    np_metric = None
    np_count = sum(np_flags)
    if np_count:
        from sklearn.metrics import mean_squared_error, r2_score

        mask = np.asarray(np_flags, dtype=bool)
        ya = np.asarray(y, dtype=float)
        pa = np.asarray(oof, dtype=float)
        if mask.sum() >= 2:
            np_r2 = float(r2_score(ya[mask], pa[mask]))
            np_rmse = float(np.sqrt(mean_squared_error(ya[mask], pa[mask])))
            np_metric = {"r2": round(np_r2, 4), "rmse": round(np_rmse, 4), "n": int(mask.sum())}
            print(
                f"Natural-product subset (n={np_metric['n']}): R²={np_metric['r2']}  "
                f"RMSE={np_metric['rmse']}. GDSC is synthetic-drug-biased; treat this as the "
                f"honest estimate for the population NaturaScreen actually screens."
            )
        else:
            print(
                f"Natural-product subset too small (n={int(np_count)}) for a separate metric; "
                f"GDSC remains synthetic-drug-biased."
            )

    # Fit the final model on ALL compounds and persist with the AD/metric meta sidecar.
    final = _xgb_regressor(args.seed)
    final.fit(np.asarray(X, dtype=float), np.asarray(y, dtype=float))
    meta = model.ResponseMeta(
        feature_keys=list(FEATURE_KEYS),
        training_onbits=onbits,
        cv_metric=cv_metric,
        source=GDSC1_SOURCE,
        natural_product_metric=np_metric,
        extra={"dropped_by_rdkit": dropped, "target_unit": "ln(IC50 µM)"},
    )
    artifacts = Path(args.artifacts) if args.artifacts else None
    model.save(final, meta, artifacts)
    print(
        f"Saved model -> {model.model_path(artifacts)}\n"
        f"Saved meta  -> {model.meta_path(artifacts)}\n"
        f"Set RESPONSE_MODEL_READY=true to activate the adapter."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
