"""The experiment pipeline: score every compound, rank, and run the top compound's sim.

Order (PRD §4): gather sub-scores from the real adapters (docking, neoantigen, response)
→ normalize + combine (scoring service) → persist auditable effectiveness rows → run the
agent simulation for the top compound at its score → persist the run.

Adapters are looked up through ``gather_subscores``. Until an adapter is provisioned it
returns ``None`` for its channel (honest "unavailable", never a fabricated number), and
the scoring service simply excludes it and renormalizes. So the pipeline is correct today
and gains signal as each adapter lands — no code here changes when they do.
"""

from __future__ import annotations

import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..disclaimer import SIMULATION_NOTICE
from ..models import (
    Compound,
    EffectivenessScore,
    Experiment,
    ExperimentStatus,
    SimulationRun,
)
from .scoring.scoring import score_compound, rank_results
from .simulation.engine import SimConfig, simulate
from .simulation.stream import reduction_pct
from .subscores import gather_subscores

log = logging.getLogger(__name__)


async def run_pipeline(session: AsyncSession, experiment_id: int) -> None:
    """Run (or re-run) the full pipeline for one experiment, mutating its rows in place."""
    experiment = (
        await session.execute(select(Experiment).where(Experiment.id == experiment_id))
    ).scalar_one_or_none()
    if experiment is None:
        raise ValueError(f"experiment {experiment_id} not found")

    experiment.status = ExperimentStatus.running
    experiment.error = None
    await session.commit()

    try:
        compounds = list(
            (
                await session.execute(
                    select(Compound).where(Compound.id.in_(experiment.compound_set or []))
                )
            )
            .scalars()
            .all()
        )
        if not compounds:
            experiment.status = ExperimentStatus.failed
            experiment.error = "experiment has no compounds"
            await session.commit()
            return

        weights = experiment.weights or None

        # Clear any prior results (idempotent re-runs).
        await session.execute(
            delete(EffectivenessScore).where(EffectivenessScore.experiment_id == experiment_id)
        )
        await session.execute(
            delete(SimulationRun).where(SimulationRun.experiment_id == experiment_id)
        )

        results = {}
        for compound in compounds:
            raw = await gather_subscores(session, experiment, compound)
            results[compound.id] = score_compound(raw, weights)

        ranks = rank_results(results)

        score_rows: dict[int, EffectivenessScore] = {}
        for compound in compounds:
            res = results[compound.id]
            row = EffectivenessScore(
                experiment_id=experiment_id,
                compound_id=compound.id,
                binding_score=res.normalized.get("binding"),
                neoantigen_score=res.normalized.get("neoantigen"),
                response_score=res.normalized.get("response"),
                simulation_score=res.normalized.get("simulation"),
                combined_score=res.combined_score,
                rank=ranks[compound.id],
                breakdown={"channels": res.breakdown, "warnings": res.warnings},
            )
            session.add(row)
            score_rows[compound.id] = row

        # Run the illustrative simulation for the top-ranked compound.
        top_id = next(cid for cid, r in ranks.items() if r == 1)
        effectiveness = results[top_id].combined_score
        config = SimConfig(seed=experiment.seed)
        treated_final = 0
        untreated_final = 0
        for frame in simulate(config, effectiveness):
            treated_final = frame.population
            untreated_final = frame.baseline_population
        reduction = reduction_pct(treated_final, untreated_final)

        session.add(
            SimulationRun(
                experiment_id=experiment_id,
                compound_id=top_id,
                baseline_population=untreated_final,
                final_population=treated_final,
                reduction_pct=reduction,
                illustrative_notice=SIMULATION_NOTICE,
            )
        )
        # Persist the (illustrative) simulation reduction as the top compound's sim sub-score.
        score_rows[top_id].simulation_score = round(reduction / 100.0, 4)

        experiment.status = ExperimentStatus.completed
        await session.commit()
        log.info("experiment %s completed; top compound %s", experiment_id, top_id)
    except Exception as exc:  # noqa: BLE001 — record failure, don't crash the worker
        await session.rollback()
        experiment.status = ExperimentStatus.failed
        experiment.error = str(exc)
        await session.commit()
        log.exception("experiment %s failed", experiment_id)
        raise


async def top_effectiveness(session: AsyncSession, experiment_id: int) -> float:
    """Effectiveness of the experiment's top-ranked compound (0.0 if not yet scored)."""
    row = (
        await session.execute(
            select(EffectivenessScore)
            .where(EffectivenessScore.experiment_id == experiment_id)
            .order_by(EffectivenessScore.rank)
            .limit(1)
        )
    ).scalar_one_or_none()
    return float(row.combined_score) if row else 0.0
