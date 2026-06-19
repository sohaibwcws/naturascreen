"""MHCflurry-backed peptide-MHC class I presentation prediction.

MHCflurry pulls in TensorFlow and scikit-learn and its trained models are a
multi-hundred-MB download that is never committed (provisioned with
``make data-mhcflurry``). So both the import and the model load happen lazily,
inside ``predict_presentation`` — importing this module costs nothing and never
requires TensorFlow, which is what lets the scoring pipeline import the neoantigen
adapter unconditionally.

When the dependency or its models are absent we raise ``AdapterUnavailable`` so
the caller can surface an honest 503 instead of fabricating a presentation score.
This module never invents a number.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

from ...config import get_settings
from ..subscores import AdapterUnavailable


@lru_cache(maxsize=1)
def _load_predictor() -> Any:
    """Load (once, process-lifetime cached) the MHCflurry presentation predictor.

    Loading the affinity + processing neural networks is expensive, so the
    instance is memoised. Any failure — mhcflurry not installed, or its models
    not downloaded — is surfaced as ``AdapterUnavailable`` rather than propagated,
    so the channel degrades honestly to "unavailable".
    """
    try:
        from mhcflurry import Class1PresentationPredictor
    except Exception as exc:  # noqa: BLE001 — ImportError or TensorFlow init failure
        raise AdapterUnavailable(
            "MHCflurry is not installed in this image"
        ) from exc
    try:
        return Class1PresentationPredictor.load()
    except Exception as exc:  # noqa: BLE001 — models not downloaded / unreadable
        raise AdapterUnavailable(
            "MHCflurry models are not provisioned — run make data-mhcflurry"
        ) from exc


def predict_presentation(peptides: list[str], alleles: list[str]) -> list[dict]:
    """Predict peptide-MHC class I presentation for every (peptide, allele) pair.

    Returns one dict per pair::

        {"peptide": str, "allele": str, "affinity_nM": float | None,
         "presentation_rank": float | None}

    where ``affinity_nM`` is the predicted binding affinity (KD in nM, lower =
    stronger) and ``presentation_rank`` is MHCflurry's presentation percentile
    rank (0-100, lower = stronger presentation) — the raw unit the neoantigen
    scoring window expects.

    Each allele is submitted as its own MHCflurry "sample" so ``predict`` emits a
    row per (peptide, allele) instead of collapsing to the single best allele per
    peptide. Allele strings round-trip verbatim (e.g. ``HLA-A*02:01``).

    Raises
    ------
    AdapterUnavailable
        If ``get_settings().mhcflurry_ready`` is False, or mhcflurry / its models
        cannot be loaded.
    """
    if not get_settings().mhcflurry_ready:
        raise AdapterUnavailable("MHCflurry not provisioned — run make data-mhcflurry")

    clean_peptides = [p.strip().upper() for p in peptides if p and p.strip()]

    clean_alleles: list[str] = []
    seen: set[str] = set()
    for allele in alleles:
        name = allele.strip()
        if name and name not in seen:
            seen.add(name)
            clean_alleles.append(name)

    if not clean_peptides or not clean_alleles:
        return []

    predictor = _load_predictor()

    # One sample per allele -> one output row per (peptide, allele). The sample
    # name is the caller's allele string, so it round-trips into the result.
    sample_alleles = {allele: [allele] for allele in clean_alleles}
    frame = predictor.predict(
        peptides=clean_peptides,
        alleles=sample_alleles,
        include_affinity_percentile=False,
        verbose=0,
        throw=False,  # a single unsupported peptide must not abort the batch
    )

    results: list[dict] = []
    for row in frame.itertuples(index=False):
        results.append(
            {
                "peptide": str(row.peptide),
                "allele": str(row.sample_name),
                "affinity_nM": _finite_or_none(getattr(row, "affinity", None)),
                "presentation_rank": _finite_or_none(
                    getattr(row, "presentation_percentile", None)
                ),
            }
        )
    return results


def _finite_or_none(value: Any) -> float | None:
    """Coerce a model output to a finite float, or ``None`` (NaN/invalid)."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None
