"""Load the curated cancer-target registry into the Target table.

Run inside the api / worker container (needs the database):

    python -m naturascreen.services.docking.curate_targets

Each registry entry is upserted by ``(pdb_id, gene)`` so re-running updates existing rows
in place rather than creating duplicates. Every curated target is written with
``type=protein``, ``dockable=True``, and the full docking box populated, which is exactly
the state the docking adapter requires before it will run. ``make curate-targets`` invokes
this module.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import get_sessionmaker
from ...models import Target, TargetType
from .targets_registry import TARGETS, TargetEntry

log = logging.getLogger(__name__)


async def upsert_targets(
    session: AsyncSession, registry: list[TargetEntry] = TARGETS
) -> int:
    """Upsert the docking-target registry into the database. Returns the rows written."""
    written = 0
    for entry in registry:
        cx, cy, cz = entry["box_center"]
        sx, sy, sz = entry["box_size"]

        target = (
            await session.execute(
                select(Target).where(
                    Target.pdb_id == entry["pdb_id"], Target.gene == entry["gene"]
                )
            )
        ).scalar_one_or_none()

        if target is None:
            target = Target(pdb_id=entry["pdb_id"], gene=entry["gene"])
            session.add(target)

        target.type = TargetType.protein
        target.description = entry["description"]
        target.dockable = True
        target.box_center_x = cx
        target.box_center_y = cy
        target.box_center_z = cz
        target.box_size_x = sx
        target.box_size_y = sy
        target.box_size_z = sz
        target.box_source = entry["box_source"]
        written += 1

    await session.commit()
    return written


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with get_sessionmaker()() as session:
        written = await upsert_targets(session)
    log.info("curated %d docking targets into the Target table", written)


if __name__ == "__main__":
    asyncio.run(main())
