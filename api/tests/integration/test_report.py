"""Candidate report: honest mechanism/caveats with no adapters, and a real PDF."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from naturascreen.disclaimer import DISCLAIMER, SIMULATION_NOTICE
from naturascreen.models import Compound, Experiment, ExperimentStatus
from naturascreen.services.compounds.coconut import CompoundRecord
from naturascreen.services.compounds.service import upsert_compounds
from naturascreen.services.pipeline import run_pipeline
from naturascreen.services.report.report import build_report, render_pdf


async def _run(session) -> int:
    await upsert_compounds(
        session,
        [CompoundRecord("CNP1", "Alpha", "CCO", None, 1), CompoundRecord("CNP2", "Beta", "CCN", None, 1)],
        with_descriptors=False,
    )
    ids = [c.id for c in (await session.execute(select(Compound))).scalars().all()]
    exp = Experiment(compound_set=ids, weights={}, seed=1, status=ExperimentStatus.created)
    session.add(exp)
    await session.commit()
    await session.refresh(exp)
    await run_pipeline(session, exp.id)
    return exp.id


async def test_report_is_honest_without_adapters(session):
    exp_id = await _run(session)
    report = await build_report(session, exp_id)
    assert report is not None
    assert report.disclaimer == DISCLAIMER
    assert report.illustrative_notice == SIMULATION_NOTICE
    assert report.rank == 1
    # No adapters -> mechanism states nothing was computed, claims no binding/response.
    assert "No docking" in report.predicted_mechanism
    assert "illustrative" in report.predicted_mechanism.lower()
    # Standard caveats always present.
    assert any("research hypothesis" in c for c in report.caveats)
    assert any("illustration of the effectiveness score" in c for c in report.caveats)


async def test_report_none_before_run(session):
    exp = Experiment(compound_set=[1], weights={}, seed=0, status=ExperimentStatus.created)
    session.add(exp)
    await session.commit()
    await session.refresh(exp)
    assert await build_report(session, exp.id) is None


async def test_pdf_renders(session):
    pytest.importorskip("reportlab")
    exp_id = await _run(session)
    report = await build_report(session, exp_id)
    assert report is not None
    pdf = render_pdf(report)
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 800
