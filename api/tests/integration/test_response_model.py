"""Response model persistence round-trip + the adapter's availability gate.

Skips entirely where ``xgboost`` is absent (the ML stack is an optional extra). The
"synthetic descriptor rows" here exercise the save/load/predict plumbing in ``model.py``
only — they are NOT training data fed to the production trainer. ``train.py`` is the thing
that refuses fabricated data; ``model.py`` is dependency plumbing and is fair to test with
arbitrary numeric rows.
"""

from __future__ import annotations

import pytest

xgb = pytest.importorskip("xgboost")

import numpy as np  # noqa: E402

from naturascreen.config import get_settings  # noqa: E402
from naturascreen.models import Compound, Experiment  # noqa: E402
from naturascreen.services.compounds.descriptors import FEATURE_KEYS  # noqa: E402
from naturascreen.services.response import adapter, model  # noqa: E402
from naturascreen.services.response.features import feature_length  # noqa: E402
from naturascreen.services.subscores import AdapterUnavailable  # noqa: E402


_TISSUE_VOCAB = ["lung", "skin"]


def _toy_model_and_meta(seed: int = 0):
    """A tiny fitted regressor over the real feature dimensionality + a valid meta sidecar."""
    rng = np.random.default_rng(seed)
    n_feat = feature_length(_TISSUE_VOCAB)
    X = rng.normal(size=(24, n_feat))
    coef = rng.normal(size=n_feat)
    y = X @ coef + rng.normal(scale=0.01, size=24)  # learnable linear target
    reg = xgb.XGBRegressor(n_estimators=20, max_depth=3, random_state=seed)
    reg.fit(X, y)
    meta = model.ResponseMeta(
        feature_keys=list(FEATURE_KEYS),
        training_onbits=[[1, 2, 3], [4, 5, 6]],
        cv_metric={"random": {"r2": 0.0}, "leave_compounds_out": {"r2": 0.0}},
        source="test",
        tissue_vocab=_TISSUE_VOCAB,
    )
    return reg, meta, X


def test_save_load_predict_roundtrip(tmp_path):
    reg, meta, X = _toy_model_and_meta()
    model.save(reg, meta, tmp_path)
    assert model.model_path(tmp_path).exists()
    assert model.meta_path(tmp_path).exists()

    loaded, loaded_meta = model.load(tmp_path)
    assert loaded_meta.feature_keys == list(FEATURE_KEYS)
    assert loaded_meta.training_onbits == [[1, 2, 3], [4, 5, 6]]
    assert loaded_meta.source == "test"

    # Predictions survive the save/load round-trip bit-for-bit (within float tolerance).
    assert np.allclose(reg.predict(X), loaded.predict(X), atol=1e-5)


def test_is_ready_requires_both_files_and_flag(tmp_path, monkeypatch):
    reg, meta, _ = _toy_model_and_meta()
    settings = get_settings()

    # Flag on but no files -> not ready (half-provisioned worker).
    monkeypatch.setattr(settings, "response_model_ready", True)
    assert model.is_ready(tmp_path) is False

    model.save(reg, meta, tmp_path)
    # Files present but flag off -> not ready (operator hasn't activated it).
    monkeypatch.setattr(settings, "response_model_ready", False)
    assert model.is_ready(tmp_path) is False

    # Both true -> ready.
    monkeypatch.setattr(settings, "response_model_ready", True)
    assert model.is_ready(tmp_path) is True


async def test_adapter_raises_adapterunavailable_with_no_checkpoint(tmp_path, monkeypatch):
    # Point the adapter's default artifacts dir at an empty dir and ensure the flag is off.
    # With no checkpoint the channel MUST be honestly unavailable, never a fabricated number.
    monkeypatch.setattr(model, "artifacts_dir", lambda: tmp_path)
    monkeypatch.setattr(get_settings(), "response_model_ready", False)

    compound = Compound(name="x", smiles="CCO", source_db="test", molecular_descriptors={})
    experiment = Experiment(compound_set=[], weights={}, seed=0)
    with pytest.raises(AdapterUnavailable):
        await adapter.score(None, experiment, compound)


async def test_adapter_predicts_persists_and_flags_ood(tmp_path, monkeypatch, session):
    """End-to-end: provisioned model -> adapter predicts ln(IC50), persists row, flags OOD."""
    from sqlalchemy import select

    from naturascreen.models import ResponsePrediction

    reg, meta, _ = _toy_model_and_meta()
    # Training fingerprints the query compound shares no bits with -> out-of-distribution.
    meta.training_onbits = [[1000, 1001, 1002], [2000, 2001]]
    model.save(reg, meta, tmp_path)

    monkeypatch.setattr(model, "artifacts_dir", lambda: tmp_path)
    monkeypatch.setattr(get_settings(), "response_model_ready", True)

    compound = Compound(
        name="curcumin-like",
        smiles="CCO",
        source_db="test",
        molecular_descriptors={
            "molecular_weight": 368.0,
            "logp": 3.0,
            "tpsa": 90.0,
            "ecfp4_onbits": [1, 2, 3],  # disjoint from training -> nn_tanimoto 0
            "ecfp4_nbits": 2048,
        },
    )
    session.add(compound)
    experiment = Experiment(compound_set=[], weights={}, seed=0)
    session.add(experiment)
    await session.commit()
    await session.refresh(compound)
    await session.refresh(experiment)

    raw = await adapter.score(session, experiment, compound)
    await session.commit()

    assert isinstance(raw, float)  # raw ln(IC50) returned, not dropped
    row = (
        await session.execute(
            select(ResponsePrediction).where(ResponsePrediction.compound_id == compound.id)
        )
    ).scalar_one()
    assert row.cell_line == "panel-median"
    assert row.nn_tanimoto == 0.0
    assert row.applicability_in_domain is False  # honestly flagged out-of-distribution
    assert row.predicted_ic50 > 0.0  # exp(ln IC50) is a positive µM concentration


async def test_adapter_rerun_is_idempotent(tmp_path, monkeypatch, session):
    """Re-running the adapter replaces, never duplicates, its prediction row."""
    from sqlalchemy import func, select

    from naturascreen.models import ResponsePrediction

    reg, meta, _ = _toy_model_and_meta()
    model.save(reg, meta, tmp_path)
    monkeypatch.setattr(model, "artifacts_dir", lambda: tmp_path)
    monkeypatch.setattr(get_settings(), "response_model_ready", True)

    compound = Compound(
        name="c", smiles="CCO", source_db="test",
        molecular_descriptors={"ecfp4_onbits": [1, 2], "ecfp4_nbits": 2048},
    )
    session.add(compound)
    experiment = Experiment(compound_set=[], weights={}, seed=0)
    session.add(experiment)
    await session.commit()
    await session.refresh(compound)
    await session.refresh(experiment)

    await adapter.score(session, experiment, compound)
    await adapter.score(session, experiment, compound)
    await session.commit()

    count = (
        await session.execute(
            select(func.count())
            .select_from(ResponsePrediction)
            .where(ResponsePrediction.compound_id == compound.id)
        )
    ).scalar_one()
    assert count == 1
