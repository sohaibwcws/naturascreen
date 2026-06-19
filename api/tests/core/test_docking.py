"""Docking adapter gating + curated-box registry (pure: no DB, no Vina).

These assert the single most important rule of the binding channel: never produce a
number without a curated box, the Vina binary, and a prepared receptor. The heavy
docking stack (vina/meeko/rdkit) is never reached here.

The adapter imports SQLAlchemy (it persists DockingResult rows), which the dependency-
light ``test-core`` environment does not install, so the module is skipped there and runs
under the full ``make test`` suite.
"""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("sqlalchemy")

from naturascreen.models import Compound, Experiment, Target  # noqa: E402
from naturascreen.services.docking.adapter import _parse_vina_affinity, _resolve_box, score  # noqa: E402
from naturascreen.services.docking.targets_registry import TARGETS  # noqa: E402
from naturascreen.services.subscores import AdapterUnavailable  # noqa: E402


class _FakeSession:
    """Minimal stand-in for AsyncSession.get — gating raises before any other DB use."""

    def __init__(self, target: Target | None) -> None:
        self._target = target

    async def get(self, _model, _pk):  # noqa: D401 — mimics AsyncSession.get
        return self._target


def _boxed_target() -> Target:
    """A fully curated, dockable target (EGFR-style box)."""
    return Target(
        id=1,
        pdb_id="1M17",
        gene="EGFR",
        dockable=True,
        box_center_x=23.0,
        box_center_y=0.0,
        box_center_z=56.0,
        box_size_x=30.0,
        box_size_y=30.0,
        box_size_z=30.0,
        box_source="test box",
    )


def test_resolve_box_returns_center_and_size_for_curated_target():
    center, size = _resolve_box(_boxed_target())
    assert center == [23.0, 0.0, 56.0]
    assert size == [30.0, 30.0, 30.0]


def test_resolve_box_rejects_undockable_target():
    target = _boxed_target()
    target.dockable = False
    with pytest.raises(AdapterUnavailable):
        _resolve_box(target)


def test_resolve_box_rejects_partial_box():
    target = _boxed_target()
    target.box_center_z = None  # an absent coordinate must disqualify the whole box
    with pytest.raises(AdapterUnavailable):
        _resolve_box(target)


def test_score_raises_without_box():
    target = _boxed_target()
    target.dockable = False
    exp = Experiment(id=1, target_id=1, seed=0)
    comp = Compound(id=1, name="x", smiles="CCO", source_db="TEST")
    with pytest.raises(AdapterUnavailable):
        asyncio.run(score(_FakeSession(target), exp, comp))


def test_score_raises_when_target_missing():
    exp = Experiment(id=1, target_id=999, seed=0)
    comp = Compound(id=1, name="x", smiles="CCO", source_db="TEST")
    with pytest.raises(AdapterUnavailable):
        asyncio.run(score(_FakeSession(None), exp, comp))


def test_score_raises_when_experiment_has_no_target():
    exp = Experiment(id=1, target_id=None, seed=0)
    comp = Compound(id=1, name="x", smiles="CCO", source_db="TEST")
    with pytest.raises(AdapterUnavailable):
        asyncio.run(score(_FakeSession(_boxed_target()), exp, comp))


def test_score_raises_when_receptor_absent():
    # A fully curated, dockable target still cannot dock without a prepared receptor
    # PDBQT on disk; the adapter must refuse rather than fabricate an affinity.
    exp = Experiment(id=1, target_id=1, seed=0)
    comp = Compound(id=1, name="x", smiles="CCO", source_db="TEST")
    with pytest.raises(AdapterUnavailable):
        asyncio.run(score(_FakeSession(_boxed_target()), exp, comp))


def test_registry_has_curated_dockable_targets():
    assert len(TARGETS) >= 4
    seen_pdb = set()
    for entry in TARGETS:
        assert entry["gene"], "gene symbol required"
        assert entry["pdb_id"], "PDB id required"
        assert entry["description"].strip()
        assert len(entry["box_center"]) == 3
        assert len(entry["box_size"]) == 3
        assert all(isinstance(c, (int, float)) for c in entry["box_center"])
        assert all(isinstance(s, (int, float)) and s > 0 for s in entry["box_size"])
        assert entry["box_source"].strip(), "provenance citation required"
        seen_pdb.add(entry["pdb_id"])
    assert len(seen_pdb) == len(TARGETS), "PDB ids must be unique"


def test_parse_vina_affinity_takes_best_pose():
    out = (
        "MODEL 1\n"
        "REMARK VINA RESULT:    -11.4      0.000      0.000\n"
        "ENDMDL\n"
        "MODEL 2\n"
        "REMARK VINA RESULT:    -9.2       1.234      2.345\n"
        "ENDMDL\n"
    )
    assert _parse_vina_affinity(out) == -11.4
