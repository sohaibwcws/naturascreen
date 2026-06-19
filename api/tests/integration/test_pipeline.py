"""Experiment pipeline behavior with no adapters provisioned (the spine state)."""

from __future__ import annotations

from sqlalchemy import select

from naturascreen.disclaimer import SIMULATION_NOTICE
from naturascreen.models import (
    Compound,
    EffectivenessScore,
    Experiment,
    ExperimentStatus,
    SimulationRun,
)
from naturascreen.services.compounds.coconut import CompoundRecord
from naturascreen.services.compounds.service import upsert_compounds
from naturascreen.services.pipeline import run_pipeline


async def _seed_compounds(session) -> list[int]:
    await upsert_compounds(
        session,
        [
            CompoundRecord("CNP1", "Alpha", "CCO", None, 1),
            CompoundRecord("CNP2", "Beta", "CCN", None, 1),
        ],
        with_descriptors=False,
    )
    return [c.id for c in (await session.execute(select(Compound))).scalars().all()]


async def test_pipeline_completes_and_persists_honestly(session):
    ids = await _seed_compounds(session)
    exp = Experiment(compound_set=ids, weights={}, seed=1, status=ExperimentStatus.created)
    session.add(exp)
    await session.commit()
    await session.refresh(exp)

    await run_pipeline(session, exp.id)
    await session.refresh(exp)
    assert exp.status == ExperimentStatus.completed

    scores = (
        (await session.execute(select(EffectivenessScore).where(EffectivenessScore.experiment_id == exp.id)))
        .scalars()
        .all()
    )
    assert len(scores) == 2
    # No adapters provisioned -> every sub-score absent -> combined score 0, nothing faked.
    assert all(s.combined_score == 0.0 for s in scores)
    assert all(s.binding_score is None and s.response_score is None for s in scores)

    sim = (
        await session.execute(select(SimulationRun).where(SimulationRun.experiment_id == exp.id))
    ).scalar_one()
    assert sim.illustrative_notice == SIMULATION_NOTICE
    # At effectiveness 0 the treated run equals the untreated baseline -> no reduction claimed.
    assert sim.reduction_pct == 0.0
    assert sim.final_population == sim.baseline_population


async def test_pipeline_is_idempotent_on_rerun(session):
    ids = await _seed_compounds(session)
    exp = Experiment(compound_set=ids, weights={}, seed=4, status=ExperimentStatus.created)
    session.add(exp)
    await session.commit()
    await session.refresh(exp)

    await run_pipeline(session, exp.id)
    await run_pipeline(session, exp.id)

    scores = (
        (await session.execute(select(EffectivenessScore).where(EffectivenessScore.experiment_id == exp.id)))
        .scalars()
        .all()
    )
    sims = (
        (await session.execute(select(SimulationRun).where(SimulationRun.experiment_id == exp.id)))
        .scalars()
        .all()
    )
    assert len(scores) == 2  # not duplicated
    assert len(sims) == 1


async def test_pipeline_fails_cleanly_with_no_compounds(session):
    exp = Experiment(compound_set=[], weights={}, seed=0, status=ExperimentStatus.created)
    session.add(exp)
    await session.commit()
    await session.refresh(exp)

    await run_pipeline(session, exp.id)
    await session.refresh(exp)
    assert exp.status == ExperimentStatus.failed
    assert exp.error and "no compounds" in exp.error
