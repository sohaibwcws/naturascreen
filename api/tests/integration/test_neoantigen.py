"""Neoantigen service persistence/ranking and adapter gating (sqlite, no TensorFlow).

The MHCflurry predictor is monkeypatched to a fake, so these tests never import
TensorFlow — they exercise our persistence, ranking, and target-match logic, not
the model. The ``session`` fixture is the shared in-memory SQLite session.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from naturascreen.models import Compound, Experiment, Neoantigen, Target, TargetType
from naturascreen.services.neoantigen import adapter, service
from naturascreen.services.subscores import AdapterUnavailable


def _fake_predictions(peptides: list[str], alleles: list[str]) -> list[dict]:
    """Deterministic stand-in for MHCflurry: one row per (peptide, allele).

    Presentation rank is assigned in *reverse* peptide order so the service's
    ascending sort is actually observable (returned unsorted on purpose).
    """
    out: list[dict] = []
    for i, pep in enumerate(peptides):
        for allele in alleles:
            out.append(
                {
                    "peptide": pep,
                    "allele": allele,
                    "affinity_nM": 100.0 * (i + 1),
                    "presentation_rank": float(len(peptides) - i),
                }
            )
    return out


async def test_predict_persists_and_ranks(session, monkeypatch):
    monkeypatch.setattr(service, "predict_presentation", _fake_predictions)

    rows = await service.predict(
        session,
        tumor_type="melanoma",
        alleles=["HLA-A*02:01"],
        peptides=["AAAAAAAA", "CCCCCCCC", "DDDDDDDD"],
    )

    # One persisted Neoantigen row per (peptide, allele).
    stored = (await session.execute(select(Neoantigen))).scalars().all()
    assert len(stored) == 3
    assert {r.tumor_type for r in stored} == {"melanoma"}
    assert {r.mhc_allele for r in stored} == {"HLA-A*02:01"}
    assert all(r.id is not None for r in stored)

    # Returned ranked by presentation_rank ascending (strongest presentation first).
    ranks = [r.presentation_rank for r in rows]
    assert ranks == sorted(ranks)
    assert rows[0].peptide == "DDDDDDDD"  # lowest fake rank -> ranked first
    assert rows[0].binding_score is not None


async def test_binder_class_thresholds():
    assert service.binder_class(0.3) == "strong"
    assert service.binder_class(service.STRONG_RANK) == "strong"
    assert service.binder_class(1.5) == "weak"
    assert service.binder_class(service.WEAK_RANK) == "weak"
    assert service.binder_class(5.0) == "non-binder"
    assert service.binder_class(None) == "unscored"


async def test_predict_propagates_unavailable_without_writing(session, monkeypatch):
    def _raise(peptides, alleles):
        raise AdapterUnavailable("not provisioned")

    monkeypatch.setattr(service, "predict_presentation", _raise)

    with pytest.raises(AdapterUnavailable):
        await service.predict(session, "melanoma", ["HLA-A*02:01"], ["AAAAAAAA"])

    stored = (await session.execute(select(Neoantigen))).scalars().all()
    assert stored == []  # nothing fabricated or half-written


async def test_adapter_raises_when_experiment_has_no_target(session):
    compound = Compound(name="Alpha", smiles="CCO", source_db="TEST")
    exp = Experiment(compound_set=[], weights={}, seed=0)
    session.add_all([compound, exp])
    await session.commit()
    await session.refresh(exp)
    await session.refresh(compound)

    with pytest.raises(AdapterUnavailable):
        await adapter.score(session, exp, compound)


async def test_adapter_raises_for_protein_target(session):
    target = Target(type=TargetType.protein, gene="EGFR")
    compound = Compound(name="Alpha", smiles="CCO", source_db="TEST")
    session.add_all([target, compound])
    await session.commit()
    await session.refresh(target)
    await session.refresh(compound)

    exp = Experiment(compound_set=[], weights={}, seed=0, target_id=target.id)
    session.add(exp)
    await session.commit()
    await session.refresh(exp)

    with pytest.raises(AdapterUnavailable):
        await adapter.score(session, exp, compound)


async def test_adapter_raises_for_neoantigen_target_without_match(session):
    target = Target(type=TargetType.neoantigen, gene="KRAS_G12D")
    compound = Compound(name="Alpha", smiles="CCO", source_db="TEST")
    # A stored neoantigen for a *different* tumor — must not match.
    other = Neoantigen(
        tumor_type="BRAF_V600E",
        peptide="GLATEKSRW",
        mhc_allele="HLA-A*02:01",
        presentation_rank=0.4,
    )
    session.add_all([target, compound, other])
    await session.commit()
    await session.refresh(target)
    await session.refresh(compound)

    exp = Experiment(compound_set=[], weights={}, seed=0, target_id=target.id)
    session.add(exp)
    await session.commit()
    await session.refresh(exp)

    with pytest.raises(AdapterUnavailable):
        await adapter.score(session, exp, compound)


async def test_adapter_returns_strongest_matching_rank(session):
    target = Target(type=TargetType.neoantigen, gene="KRAS_G12D")
    compound = Compound(name="Alpha", smiles="CCO", source_db="TEST")
    session.add_all(
        [
            target,
            compound,
            Neoantigen(
                tumor_type="KRAS_G12D",
                peptide="GADGVGKSA",
                mhc_allele="HLA-A*02:01",
                binding_score=120.0,
                presentation_rank=1.8,
            ),
            Neoantigen(
                tumor_type="KRAS_G12D",
                peptide="VVGADGVGK",
                mhc_allele="HLA-A*11:01",
                binding_score=40.0,
                presentation_rank=0.3,  # stronger -> should win
            ),
        ]
    )
    await session.commit()
    await session.refresh(target)
    await session.refresh(compound)

    exp = Experiment(compound_set=[], weights={}, seed=0, target_id=target.id)
    session.add(exp)
    await session.commit()
    await session.refresh(exp)

    rank = await adapter.score(session, exp, compound)
    assert rank == 0.3
