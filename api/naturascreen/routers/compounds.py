"""Compound library endpoints: search/list and detail."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Compound
from ..schemas import CompoundOut, CompoundPage
from ..services.compounds.service import search_compounds

router = APIRouter(prefix="/compounds", tags=["compounds"])


@router.get("", response_model=CompoundPage)
async def list_compounds(
    q: str | None = Query(default=None, description="name / COCONUT id / InChIKey substring"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> CompoundPage:
    items, total = await search_compounds(session, q=q, limit=limit, offset=offset)
    return CompoundPage(
        items=[CompoundOut.model_validate(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{compound_id}", response_model=CompoundOut)
async def get_compound(
    compound_id: int, session: AsyncSession = Depends(get_session)
) -> CompoundOut:
    compound = (
        await session.execute(select(Compound).where(Compound.id == compound_id))
    ).scalar_one_or_none()
    if compound is None:
        raise HTTPException(status_code=404, detail="compound not found")
    return CompoundOut.model_validate(compound)


@router.get("/{compound_id}/structure.svg")
async def compound_structure(
    compound_id: int, session: AsyncSession = Depends(get_session)
) -> Response:
    compound = (
        await session.execute(select(Compound).where(Compound.id == compound_id))
    ).scalar_one_or_none()
    if compound is None:
        raise HTTPException(status_code=404, detail="compound not found")
    from ..services.compounds.draw import draw_svg

    svg = draw_svg(compound.smiles)
    if svg is None:
        raise HTTPException(status_code=422, detail="structure could not be rendered")
    return Response(content=svg, media_type="image/svg+xml")
