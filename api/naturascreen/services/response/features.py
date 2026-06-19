"""Feature vectorization for the response model (spec §5) — pure, no heavy deps.

The response model predicts ln(IC50 µM) from a compound's scalar RDKit physicochemical
descriptors. The feature order is owned by ``compounds.descriptors.FEATURE_KEYS`` so that
training and inference agree exactly; the meta sidecar records the order used at fit time
so a drift is caught rather than silently mispredicted.

The ECFP4 fingerprint fields (``ecfp4_onbits`` / ``ecfp4_nbits``) are deliberately EXCLUDED
from the feature vector: they drive the applicability-domain Tanimoto distance to the
training set (see ``applicability``), not the regression inputs. ``FEATURE_KEYS`` already
omits them; this module simply projects onto that order.
"""

from __future__ import annotations

from ..compounds.descriptors import FEATURE_KEYS


def feature_vector(descriptors: dict) -> list[float]:
    """Project a descriptor dict onto the model's fixed scalar-feature order.

    A missing key maps to ``0.0`` so a partially-computed descriptor set still yields a
    well-formed, correctly-ordered vector. Honesty is enforced by the applicability-domain
    check downstream — not by pretending an absent descriptor is meaningful — so a degenerate
    feature vector still produces a prediction that is then flagged out-of-distribution.
    """
    return [float(descriptors.get(key, 0.0)) for key in FEATURE_KEYS]
