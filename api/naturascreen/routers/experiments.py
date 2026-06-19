"""Experiment lifecycle: create, list, run (queue or sync), and ranked results."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import (
    Compound,
    EffectivenessScore,
    Experiment,
    ExperimentStatus,
    SimulationRun,
)
from ..schemas import (
    ExperimentCreate,
    ExperimentOut,
    ExperimentResults,
    ScoredCompoundOut,
    SimulationSummary,
)
from ..services.pipeline import run_pipeline

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentOut, status_code=201)
async def create_experiment(
    body: ExperimentCreate, session: AsyncSession = Depends(get_session)
) -> ExperimentOut:
    if not body.compound_set:
        raise HTTPException(status_code=422, detail="compound_set must not be empty")
    experiment = Experiment(
        target_id=body.target_id,
        compound_set=body.compound_set,
        weights=body.weights or {},
        seed=body.seed,
        status=ExperimentStatus.created,
    )
    session.add(experiment)
    await session.commit()
    await session.refresh(experiment)
    return ExperimentOut.model_validate(experiment)


@router.get("", response_model=list[ExperimentOut])
async def list_experiments(
    limit: int = Query(default=50, ge=1, le=200), session: AsyncSession = Depends(get_session)
) -> list[ExperimentOut]:
    rows = (
        (await session.execute(select(Experiment).order_by(Experiment.id.desc()).limit(limit)))
        .scalars()
        .all()
    )
    return [ExperimentOut.model_validate(r) for r in rows]


@router.get("/{experiment_id}", response_model=ExperimentOut)
async def get_experiment(
    experiment_id: int, session: AsyncSession = Depends(get_session)
) -> ExperimentOut:
    experiment = await _load(session, experiment_id)
    return ExperimentOut.model_validate(experiment)


@router.post("/{experiment_id}/run", response_model=ExperimentOut)
async def run_experiment_endpoint(
    experiment_id: int,
    sync: bool = Query(default=False, description="run inline instead of queueing on Celery"),
    session: AsyncSession = Depends(get_session),
) -> ExperimentOut:
    experiment = await _load(session, experiment_id)
    if sync:
        await run_pipeline(session, experiment_id)
        await session.refresh(experiment)
        return ExperimentOut.model_validate(experiment)

    experiment.status = ExperimentStatus.queued
    await session.commit()
    from ..tasks.pipeline import run_experiment  # lazy: keep Celery off the import path

    run_experiment.delay(experiment_id)
    await session.refresh(experiment)
    return ExperimentOut.model_validate(experiment)


@router.get("/{experiment_id}/results", response_model=ExperimentResults)
async def experiment_results(
    experiment_id: int, session: AsyncSession = Depends(get_session)
) -> ExperimentResults:
    experiment = await _load(session, experiment_id)

    scores = (
        (
            await session.execute(
                select(EffectivenessScore)
                .where(EffectivenessScore.experiment_id == experiment_id)
                .order_by(EffectivenessScore.rank)
            )
        )
        .scalars()
        .all()
    )
    compounds = {
        c.id: c
        for c in (
            await session.execute(
                select(Compound).where(Compound.id.in_([s.compound_id for s in scores]))
            )
        )
        .scalars()
        .all()
    }
    ranked = [
        ScoredCompoundOut(
            compound_id=s.compound_id,
            name=compounds[s.compound_id].name if s.compound_id in compounds else "?",
            coconut_id=compounds[s.compound_id].coconut_id if s.compound_id in compounds else None,
            smiles=compounds[s.compound_id].smiles if s.compound_id in compounds else "",
            rank=s.rank,
            combined_score=s.combined_score,
            normalized={
                "binding": s.binding_score,
                "neoantigen": s.neoantigen_score,
                "response": s.response_score,
                "simulation": s.simulation_score,
            },
            breakdown=s.breakdown.get("channels", {}),
            warnings=s.breakdown.get("warnings", []),
        )
        for s in scores
    ]

    sim_row = (
        await session.execute(
            select(SimulationRun).where(SimulationRun.experiment_id == experiment_id).limit(1)
        )
    ).scalar_one_or_none()
    simulation = (
        SimulationSummary(
            compound_id=sim_row.compound_id,
            baseline_population=sim_row.baseline_population,
            final_population=sim_row.final_population,
            reduction_pct=sim_row.reduction_pct,
        )
        if sim_row
        else None
    )

    return ExperimentResults(
        experiment=ExperimentOut.model_validate(experiment),
        ranked=ranked,
        simulation=simulation,
    )


async def _load(session: AsyncSession, experiment_id: int) -> Experiment:
    experiment = (
        await session.execute(select(Experiment).where(Experiment.id == experiment_id))
    ).scalar_one_or_none()
    if experiment is None:
        raise HTTPException(status_code=404, detail="experiment not found")
    return experiment
