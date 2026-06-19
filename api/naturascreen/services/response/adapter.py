"""Response sub-score adapter: predicted ln(IC50 µM) from the cell-line response model.

Scientific honesty (spec §5): the model is trained on GDSC, a screen of *synthetic* drugs,
so it is out-of-distribution for most natural products — exactly the population NaturaScreen
screens. This adapter never silently trusts a prediction. It computes the ECFP4 Tanimoto
nearest-neighbour distance from the compound to the training set, flags
``applicability_in_domain`` accordingly, and persists both the flag and the distance on the
``ResponsePrediction`` row so the report can surface the out-of-distribution warning. It
still RETURNS the raw ln(IC50): the OOD flag down-weights the channel downstream rather than
dropping a measured number on the floor.

When the model is not provisioned (artifacts missing or ``response_model_ready`` false) it
raises ``AdapterUnavailable`` — the channel is then honestly absent, never fabricated.
``xgboost`` is imported lazily (inside ``model.load``); importing this module needs no heavy
dependency, which is why the pipeline can import it unconditionally.
"""

from __future__ import annotations

import math
import statistics

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import Compound, Experiment, ResponsePrediction
from ..subscores import AdapterUnavailable
from . import applicability, features, model


async def score(
    session: AsyncSession, experiment: Experiment, compound: Compound
) -> float | None:
    """Predicted ln(IC50 µM) for ``compound``, or raise ``AdapterUnavailable`` if unprovisioned."""
    if not model.is_ready():
        raise AdapterUnavailable(
            "response model not provisioned (run `make data-response` and set "
            "RESPONSE_MODEL_READY=true)"
        )

    regressor, meta = model.load()

    descriptors = compound.molecular_descriptors or {}
    # Predict across the tissue panel the model was trained on, then aggregate. The compound
    # is fixed; only the tissue context varies, so the median is the compound's typical
    # predicted potency across cancer tissue types.
    if meta.tissue_vocab:
        batch = [features.feature_vector(descriptors, t, meta.tissue_vocab) for t in meta.tissue_vocab]
    else:
        batch = [features.compound_features(descriptors)]
    preds = [float(p) for p in regressor.predict(batch)]
    ln_ic50 = float(statistics.median(preds))

    onbits = list(descriptors.get("ecfp4_onbits") or [])
    nn = applicability.nearest_neighbor_tanimoto(onbits, meta.training_onbits)
    within = applicability.in_domain(nn)

    # Idempotent re-runs: the pipeline clears scores/sims but not detail rows, so clear our
    # own prior prediction for this (experiment, compound) before persisting the new one.
    await session.execute(
        delete(ResponsePrediction)
        .where(ResponsePrediction.experiment_id == experiment.id)
        .where(ResponsePrediction.compound_id == compound.id)
    )
    session.add(
        ResponsePrediction(
            experiment_id=experiment.id,
            compound_id=compound.id,
            cell_line="panel-median",
            # Raw ln(IC50) is returned unmodified; the persisted µM value is guarded against
            # an overflow from a pathological prediction (exp argument capped at ~700).
            predicted_ic50=math.exp(min(ln_ic50, 700.0)),
            applicability_in_domain=within,
            nn_tanimoto=nn,
        )
    )
    await session.flush()
    return ln_ic50
