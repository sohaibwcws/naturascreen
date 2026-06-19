"""Feature vectorization for the response model (spec §5) — pure, no heavy deps.

A feature vector has two blocks:
1. **compound block** — scalar RDKit physicochemical descriptors (``FEATURE_KEYS`` order)
   plus a folded ECFP4 structural fingerprint (``FP_FOLD`` bits), and
2. **context block** — a one-hot of the cell line's tissue type (``tissue_vocab``).

The context block is what lets the model learn the cell-line/tissue variance the PRD
intended ("descriptors + cell-line genomics") instead of collapsing a drug to one number.
At inference the adapter predicts a compound across every tissue in the vocab and aggregates
(see ``adapter``). The full-resolution ``ecfp4_onbits`` still drive the applicability-domain
Tanimoto distance (see ``applicability``) — folding here is only for the regressor.

The vocab is owned by the trained model (recorded in its meta sidecar) so training and
inference agree exactly.
"""

from __future__ import annotations

from ..compounds.descriptors import FEATURE_KEYS

# Folded fingerprint width. 256 keeps the vector compact while preserving structural signal.
FP_FOLD = 256
COMPOUND_LENGTH = len(FEATURE_KEYS) + FP_FOLD


def compound_features(descriptors: dict) -> list[float]:
    """The compound block: scalar descriptors + folded ECFP4 fingerprint (length COMPOUND_LENGTH)."""
    scalars = [float(descriptors.get(key, 0.0)) for key in FEATURE_KEYS]
    folded = [0.0] * FP_FOLD
    for bit in descriptors.get("ecfp4_onbits") or []:
        folded[int(bit) % FP_FOLD] = 1.0
    return scalars + folded


def tissue_onehot(tissue: str, tissue_vocab: list[str]) -> list[float]:
    """One-hot the tissue against the model's vocab (all-zeros for an unknown tissue)."""
    return [1.0 if t == tissue else 0.0 for t in tissue_vocab]


def feature_vector(descriptors: dict, tissue: str, tissue_vocab: list[str]) -> list[float]:
    """Full feature vector: compound block + tissue one-hot."""
    return compound_features(descriptors) + tissue_onehot(tissue, tissue_vocab)


def feature_length(tissue_vocab: list[str]) -> int:
    return COMPOUND_LENGTH + len(tissue_vocab)
