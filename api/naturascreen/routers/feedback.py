"""Feedback loop: submit real lab results that become retraining labels (PRD §5).

A model cannot learn to find a cure when no confirmed human cure exists to train on. It
can learn which predictions hold up in a dish. Each submitted result is a structured
``LabResult`` the response model retrains on; see ``tasks.retrain`` for the scheduled job.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Compound, LabResult
from ..schemas import LabResultIn, LabResultOut

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/lab-result", response_model=LabResultOut, status_code=201)
async def submit_lab_result(
    body: LabResultIn, session: AsyncSession = Depends(get_session)
) -> LabResultOut:
    compound = (
        await session.execute(select(Compound).where(Compound.id == body.compound_id))
    ).scalar_one_or_none()
    if compound is None:
        raise HTTPException(status_code=404, detail="compound not found")

    row = LabResult(
        compound_id=body.compound_id,
        target_id=body.target_id,
        measured_ic50=body.measured_ic50,
        source=body.source,
        verified=body.verified,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return LabResultOut.model_validate(row)


@router.get("/lab-results", response_model=list[LabResultOut])
async def list_lab_results(
    limit: int = Query(default=100, ge=1, le=500),
    verified_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> list[LabResultOut]:
    stmt = select(LabResult).order_by(LabResult.id.desc()).limit(limit)
    if verified_only:
        stmt = stmt.where(LabResult.verified.is_(True))
    rows = (await session.execute(stmt)).scalars().all()
    return [LabResultOut.model_validate(r) for r in rows]
