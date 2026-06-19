"""Compound upsert + search behavior (against in-memory SQLite)."""

from __future__ import annotations

from naturascreen.services.compounds.coconut import CompoundRecord
from naturascreen.services.compounds.service import search_compounds, upsert_compounds


def _rec(cid: str, name: str, smiles: str = "CCO") -> CompoundRecord:
    return CompoundRecord(coconut_id=cid, name=name, smiles=smiles, iupac_name=None, annotation_level=1)


async def test_upsert_then_search_by_name(session):
    written = await upsert_compounds(
        session,
        [_rec("CNP1", "Curcumin"), _rec("CNP2", "Quercetin")],
        with_descriptors=False,
    )
    assert written == 2

    items, total = await search_compounds(session, q="curc")
    assert total == 1
    assert items[0].name == "Curcumin"
    assert items[0].coconut_id == "CNP1"


async def test_upsert_is_idempotent_by_coconut_id(session):
    await upsert_compounds(session, [_rec("CNP1", "Curcumin")], with_descriptors=False)
    await upsert_compounds(session, [_rec("CNP1", "Curcumin (revised)")], with_descriptors=False)

    items, total = await search_compounds(session)
    assert total == 1  # not duplicated
    assert items[0].name == "Curcumin (revised)"  # updated in place


async def test_search_pagination_caps_and_offsets(session):
    await upsert_compounds(
        session, [_rec(f"CNP{i}", f"compound-{i:02d}") for i in range(10)], with_descriptors=False
    )
    page1, total = await search_compounds(session, limit=3, offset=0)
    page2, _ = await search_compounds(session, limit=3, offset=3)
    assert total == 10
    assert [c.id for c in page1] != [c.id for c in page2]
    assert len(page1) == 3
