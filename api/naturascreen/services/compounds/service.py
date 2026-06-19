"""Database operations for the compound library: upsert from ingestion, and search."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import Compound
from .coconut import CompoundRecord


async def upsert_compounds(
    session: AsyncSession,
    records: list[CompoundRecord],
    *,
    source_db: str = "COCONUT",
    with_descriptors: bool = True,
) -> int:
    """Insert or update compounds keyed by COCONUT id. Returns the number written.

    Descriptors are computed with RDKit when ``with_descriptors`` is set; this is skipped
    in tests that exercise the upsert without the heavy dependency.
    """
    compute = None
    if with_descriptors:
        from .descriptors import compute as _compute  # lazy: RDKit only where available

        compute = _compute

    written = 0
    for rec in records:
        inchikey: str | None = None
        descriptors: dict = {}
        if compute is not None:
            result = compute(rec.smiles)
            if result is None:
                continue  # invalid SMILES — never store an undockable, unparseable row
            inchikey, descriptors = result

        refs = [{"db": "COCONUT", "id": rec.coconut_id}]
        if rec.iupac_name:
            refs.append({"iupac_name": rec.iupac_name})

        existing = (
            await session.execute(select(Compound).where(Compound.coconut_id == rec.coconut_id))
        ).scalar_one_or_none()

        if existing is None:
            session.add(
                Compound(
                    name=rec.name,
                    smiles=rec.smiles,
                    inchikey=inchikey,
                    source_db=source_db,
                    coconut_id=rec.coconut_id,
                    molecular_descriptors=descriptors,
                    references=refs,
                )
            )
        else:
            existing.name = rec.name
            existing.smiles = rec.smiles
            if inchikey:
                existing.inchikey = inchikey
            if descriptors:
                existing.molecular_descriptors = descriptors
            existing.references = refs
        written += 1

    await session.commit()
    return written


async def search_compounds(
    session: AsyncSession, *, q: str | None = None, limit: int = 50, offset: int = 0
) -> tuple[list[Compound], int]:
    """Search compounds by name / COCONUT id / InChIKey substring; paginated."""
    limit = max(1, min(limit, 200))
    stmt = select(Compound)
    count_stmt = select(func.count()).select_from(Compound)
    if q:
        pattern = f"%{q.strip()}%"
        cond = or_(
            Compound.name.ilike(pattern),
            Compound.coconut_id.ilike(pattern),
            Compound.inchikey.ilike(pattern),
        )
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    total = (await session.execute(count_stmt)).scalar_one()
    rows = (
        (await session.execute(stmt.order_by(Compound.id).limit(limit).offset(offset)))
        .scalars()
        .all()
    )
    return list(rows), total
