"""Scheduled retraining on real lab results (the feedback loop, PRD §5).

A model cannot learn to find a cure when none exists to train on. It can learn which
predictions hold up in a dish. This task folds verified ``LabResult`` rows into the real
GDSC training set and retrains the response model. It NEVER trains on fabricated data:
if the GDSC base is not provisioned, or there are no verified lab results, it skips with a
clear reason rather than inventing labels.
"""

from __future__ import annotations

import asyncio
import csv
import logging
import math
from pathlib import Path

from sqlalchemy import select

from ..config import get_settings
from ..db import get_sessionmaker
from ..models import Compound, LabResult
from ..services.response.train import (
    DEFAULT_CSV_NAME,
    _IC50_UM_CANDIDATES,
    _LN_IC50_CANDIDATES,
    _SMILES_CANDIDATES,
    _TISSUE_CANDIDATES,
)
from .celery_app import celery_app

log = logging.getLogger(__name__)


def _read_base_rows(base_csv: Path) -> list[tuple[str, str, float]]:
    """Read (SMILES, TISSUE, ln(IC50 µM)) rows from the GDSC export, tolerant of column names."""
    with base_csv.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        cols = reader.fieldnames or []
        scol = next((c for c in _SMILES_CANDIDATES if c in cols), None)
        lcol = next((c for c in _LN_IC50_CANDIDATES if c in cols), None)
        icol = next((c for c in _IC50_UM_CANDIDATES if c in cols), None)
        tcol = next((c for c in _TISSUE_CANDIDATES if c in cols), None)
        if not scol or not (lcol or icol):
            raise ValueError("base CSV lacks recognizable SMILES + (LN_)IC50 columns")
        rows: list[tuple[str, str, float]] = []
        for r in reader:
            smiles = (r.get(scol) or "").strip()
            if not smiles:
                continue
            if lcol and r.get(lcol):
                ln = float(r[lcol])
            elif icol and r.get(icol):
                ic50 = float(r[icol])
                if ic50 <= 0:
                    continue
                ln = math.log(ic50)
            else:
                continue
            tissue = (r.get(tcol) or "UNKNOWN").strip() if tcol else "UNKNOWN"
            rows.append((smiles, tissue, ln))
    return rows


async def _gather_lab_rows() -> list[tuple[str, str, float]]:
    """Verified lab results as (SMILES, TISSUE='UNKNOWN', ln(measured IC50 µM)) rows."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        result = await session.execute(
            select(Compound.smiles, LabResult.measured_ic50)
            .join(Compound, LabResult.compound_id == Compound.id)
            .where(LabResult.verified.is_(True))
        )
        rows: list[tuple[str, str, float]] = []
        for smiles, ic50 in result.all():
            if smiles and ic50 and ic50 > 0:
                rows.append((smiles, "UNKNOWN", math.log(float(ic50))))
        return rows


def _write_augmented(
    out_csv: Path, base: list[tuple[str, str, float]], lab: list[tuple[str, str, float]]
) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["SMILES", "TISSUE", "LN_IC50"])
        for smiles, tissue, ln in [*base, *lab]:
            writer.writerow([smiles, tissue, ln])


async def _retrain() -> dict:
    settings = get_settings()
    data_dir = Path(settings.data_dir)
    base_csv = data_dir / DEFAULT_CSV_NAME
    if not base_csv.exists():
        log.warning("base GDSC data not provisioned (%s); cannot retrain on lab results alone", base_csv)
        return {"status": "skipped", "reason": "base GDSC training data not provisioned"}

    lab_rows = await _gather_lab_rows()
    if not lab_rows:
        return {"status": "skipped", "reason": "no verified lab results"}

    base_rows = _read_base_rows(base_csv)
    augmented = data_dir / "response_train_augmented.csv"
    _write_augmented(augmented, base_rows, lab_rows)

    from ..services.response import train  # lazy: pulls pandas/xgboost only when retraining

    rc = train.main(["--csv", str(augmented)])
    log.info("retrained response model: base=%d lab=%d rc=%d", len(base_rows), len(lab_rows), rc)
    return {"status": "retrained", "base_rows": len(base_rows), "lab_rows": len(lab_rows), "rc": rc}


@celery_app.task(name="retrain_response_model")
def retrain_response_model() -> dict:
    return asyncio.run(_retrain())
