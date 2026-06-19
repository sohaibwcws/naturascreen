"""Cancer target listing. Targets are curated (with docking boxes) in the docking phase."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Target
from ..schemas import TargetOut

router = APIRouter(prefix="/targets", tags=["targets"])


@router.get("", response_model=list[TargetOut])
async def list_targets(
    dockable_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> list[TargetOut]:
    stmt = select(Target).order_by(Target.id)
    if dockable_only:
        stmt = stmt.where(Target.dockable.is_(True))
    rows = (await session.execute(stmt)).scalars().all()
    return [TargetOut.model_validate(t) for t in rows]


@router.get("/{target_id}", response_model=TargetOut)
async def get_target(target_id: int, session: AsyncSession = Depends(get_session)) -> TargetOut:
    target = (
        await session.execute(select(Target).where(Target.id == target_id))
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="target not found")
    return TargetOut.model_validate(target)
