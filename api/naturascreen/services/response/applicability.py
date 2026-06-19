"""Applicability-domain math for the response model (spec §5) — pure, no heavy deps.

The natural-product transfer problem: the response model is fit on GDSC, a screen of
*synthetic* drugs, while NaturaScreen screens natural products. A prediction is only as
trustworthy as the model's familiarity with structures like the query. We quantify that
familiarity with the Tanimoto similarity between ECFP4 on-bit sets — the query compound vs.
every training compound — and take the nearest neighbour. Below a threshold the compound is
out-of-distribution and the prediction must be treated as a weak signal at most.

All functions here operate on plain lists of integer bit indices (the ``ecfp4_onbits`` we
persist per compound), so this module is import-safe everywhere and exhaustively testable
without RDKit.
"""

from __future__ import annotations

from collections.abc import Iterable

# Default ECFP4 Tanimoto cutoff below which a compound is judged out-of-distribution.
# 0.30 is a conventional fingerprint-similarity floor for "structurally related"; it is a
# documented constant, not a tuned hyperparameter, and is surfaced wherever it is applied.
DEFAULT_AD_THRESHOLD = 0.30


def tanimoto(onbits_a: list[int], onbits_b: list[int]) -> float:
    """Tanimoto (Jaccard) similarity between two ECFP on-bit sets: ``|A∩B| / |A∪B|``.

    Identical sets give 1.0, disjoint sets give 0.0. Two empty fingerprints carry no
    structural evidence of similarity, so they return 0.0 (and avoid a 0/0): a molecule
    with no on-bits is degenerate and should be flagged out-of-domain, never silently
    trusted as a perfect match.
    """
    set_a = set(onbits_a)
    set_b = set(onbits_b)
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def nearest_neighbor_tanimoto(
    query_onbits: list[int], training_onbits_list: Iterable[list[int]]
) -> float:
    """Maximum Tanimoto similarity from ``query_onbits`` to any training fingerprint.

    Returns 0.0 for an empty training set — with no reference structures the model cannot
    claim the query is in-domain.
    """
    best = 0.0
    found = False
    for ref in training_onbits_list:
        found = True
        sim = tanimoto(query_onbits, ref)
        if sim > best:
            best = sim
    return best if found else 0.0


def in_domain(nn_tanimoto: float, threshold: float = DEFAULT_AD_THRESHOLD) -> bool:
    """True when the nearest-neighbour similarity meets the applicability-domain threshold."""
    return nn_tanimoto >= threshold
