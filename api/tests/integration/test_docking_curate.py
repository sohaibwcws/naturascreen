"""Target curation against in-memory SQLite, plus a dependency-gated ligand-prep check."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from naturascreen.models import Target, TargetType
from naturascreen.services.docking.curate_targets import upsert_targets
from naturascreen.services.docking.targets_registry import TARGETS


async def test_curation_populates_dockable_boxed_targets(session):
    written = await upsert_targets(session)
    assert written == len(TARGETS)

    targets = (await session.execute(select(Target))).scalars().all()
    assert len(targets) == len(TARGETS)

    for t in targets:
        assert t.type == TargetType.protein
        assert t.dockable is True
        assert None not in (t.box_center_x, t.box_center_y, t.box_center_z)
        assert None not in (t.box_size_x, t.box_size_y, t.box_size_z)
        assert t.box_source and t.box_source.strip()  # provenance persisted

    # Spot-check a known curated entry round-trips its cited coordinates.
    egfr = (
        await session.execute(select(Target).where(Target.gene == "EGFR"))
    ).scalar_one()
    assert egfr.pdb_id == "1M17"
    assert egfr.box_center_x == 23.0
    assert egfr.box_size_x == 30.0


async def test_curation_is_idempotent(session):
    await upsert_targets(session)
    await upsert_targets(session)

    targets = (await session.execute(select(Target))).scalars().all()
    assert len(targets) == len(TARGETS)  # upsert by (pdb_id, gene), not duplicated


def test_prepare_ligand_real_tooling():
    """Exercise the real RDKit + Meeko prep path; skips where the stack is absent."""
    pytest.importorskip("rdkit")
    pytest.importorskip("meeko")
    from naturascreen.services.docking.prep import prepare_ligand

    pdbqt = prepare_ligand("CCO", seed=1)
    assert "ROOT" in pdbqt and "ATOM" in pdbqt


def test_vina_dock_real_tooling():
    """Placeholder for the real Vina dock; skips here (no bundled receptor PDBQT)."""
    pytest.importorskip("vina")
    pytest.importorskip("meeko")
    pytest.importorskip("rdkit")
    pytest.skip("real docking requires a prepared receptor PDBQT provisioned offline")
