"""Feature vectorization for the response model (spec §5) — pure, no heavy deps.

The response model predicts ln(IC50 µM) from two blocks of features:
1. scalar RDKit physicochemical descriptors (``FEATURE_KEYS`` order), and
2. a folded ECFP4 structural fingerprint (``FP_FOLD`` bits), which carries the
   structure–activity signal a handful of scalars cannot.

The feature order is owned here so training and inference agree exactly; the meta sidecar
records it so drift is caught rather than silently mispredicted.

Note: the FULL-resolution ``ecfp4_onbits`` still drive the applicability-domain Tanimoto
distance to the training set (see ``applicability``) — that is unchanged. Here we only fold
them into model features; folding is for the regressor, the unfolded bits guard the domain.
"""

from __future__ import annotations

from ..compounds.descriptors import FEATURE_KEYS

# Folded fingerprint width. 256 keeps the vector compact while preserving structural signal.
FP_FOLD = 256

FEATURE_LENGTH = len(FEATURE_KEYS) + FP_FOLD


def feature_vector(descriptors: dict) -> list[float]:
    """Project a descriptor dict onto the model's fixed feature order (scalars + folded FP).

    Missing scalars map to ``0.0`` so a partially-computed descriptor set still yields a
    well-formed, correctly-ordered vector; the applicability-domain check downstream flags a
    degenerate molecule rather than this function pretending an absent value is meaningful.
    """
    scalars = [float(descriptors.get(key, 0.0)) for key in FEATURE_KEYS]
    folded = [0.0] * FP_FOLD
    for bit in descriptors.get("ecfp4_onbits") or []:
        folded[int(bit) % FP_FOLD] = 1.0
    return scalars + folded
