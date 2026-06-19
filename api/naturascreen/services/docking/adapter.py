"""Binding sub-score channel: dock a compound and return its Vina affinity.

The scoring pipeline calls :func:`score` for every compound. It returns the best
AutoDock Vina binding affinity (kcal/mol, more negative = stronger) for the compound
in the target's curated search box, persisting a :class:`DockingResult` row. It raises
``AdapterUnavailable`` whenever the prerequisites for an honest dock are missing:

* the experiment has no resolvable target,
* the target is not ``dockable`` or its search box is incomplete (NEVER dock without a
  curated box — a wrong/absent box gives confident garbage),
* the Vina binary is not configured, or
* the prepared receptor PDBQT is not on disk.

Any import or runtime failure of the docking stack (vina / meeko / rdkit) is also
surfaced as ``AdapterUnavailable`` so the channel degrades to "unavailable" instead of
crashing the worker. The seam (``gather_subscores``) turns ``AdapterUnavailable`` into a
missing channel, which the scoring service excludes and renormalizes.

Heavy libraries are imported lazily inside :func:`_dock`; importing this module requires
no scientific dependencies.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import get_settings
from ...models import Compound, DockingResult, Experiment, Target
from ..subscores import AdapterUnavailable
from .prep import prepare_ligand

log = logging.getLogger(__name__)

# AutoDock Vina search effort and number of poses retained per dock. exhaustiveness 8 is
# the Vina default; 20 poses is the common screening setting (the best is returned).
EXHAUSTIVENESS = 8
N_POSES = 20


def _resolve_box(target: Target) -> tuple[list[float], list[float]]:
    """Return ``(center, size)`` for a dockable target, or raise ``AdapterUnavailable``.

    A target is dockable only if the flag is set and all six box coordinates are
    present. This is the gate that keeps the adapter from ever docking into an
    uncurated (and therefore meaningless) box.
    """
    coords = (
        target.box_center_x,
        target.box_center_y,
        target.box_center_z,
        target.box_size_x,
        target.box_size_y,
        target.box_size_z,
    )
    if not target.dockable or any(c is None for c in coords):
        raise AdapterUnavailable(
            f"target {target.id} is not dockable or has no curated search box"
        )
    center = [float(target.box_center_x), float(target.box_center_y), float(target.box_center_z)]
    size = [float(target.box_size_x), float(target.box_size_y), float(target.box_size_z)]
    return center, size


def _receptor_path(data_dir: str, pdb_id: str | None) -> Path | None:
    """Path to the offline-prepared rigid receptor PDBQT, or None if no PDB id."""
    if not pdb_id:
        return None
    return Path(data_dir) / "docking" / "receptors" / f"{pdb_id}.pdbqt"


def _parse_vina_affinity(pdbqt_text: str) -> float:
    """Best-pose affinity (kcal/mol) from a Vina output PDBQT (first model is best)."""
    for line in pdbqt_text.splitlines():
        if line.startswith("REMARK VINA RESULT:"):
            return float(line.split(":", 1)[1].split()[0])
    raise ValueError("no 'REMARK VINA RESULT' line in Vina output")


def _dock_cli(
    receptor_path: str, ligand_pdbqt: str, center: list[float], size: list[float], seed: int
) -> float:
    """Run the AutoDock Vina CLI binary (cross-platform fallback when the wheel is absent)."""
    import subprocess
    import tempfile
    from pathlib import Path as _P

    binary = (get_settings().vina_binary or "vina").strip()
    with tempfile.TemporaryDirectory() as td:
        lig = _P(td) / "ligand.pdbqt"
        out = _P(td) / "out.pdbqt"
        lig.write_text(ligand_pdbqt)
        cmd = [
            binary, "--receptor", receptor_path, "--ligand", str(lig),
            "--center_x", str(center[0]), "--center_y", str(center[1]), "--center_z", str(center[2]),
            "--size_x", str(size[0]), "--size_y", str(size[1]), "--size_z", str(size[2]),
            "--exhaustiveness", str(EXHAUSTIVENESS), "--seed", str(int(seed)),
            "--out", str(out),
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=900)
        return _parse_vina_affinity(out.read_text())


def _dock(
    receptor_path: str,
    smiles: str,
    center: list[float],
    size: list[float],
    seed: int,
) -> float:
    """Prepare the ligand and run AutoDock Vina; return the best affinity (kcal/mol).

    Uses the Python ``vina`` bindings when installed (the Linux worker image); otherwise
    falls back to the Vina CLI binary on PATH, so docking also runs on hosts without the
    wheel. Runs synchronously (the Vina C++ core blocks) and is invoked in a worker thread
    by :func:`score`. All heavy imports are local so the module stays dependency-light.
    """
    ligand_pdbqt = prepare_ligand(smiles, seed=seed)
    try:
        from vina import Vina
    except ImportError:
        return _dock_cli(receptor_path, ligand_pdbqt, center, size, seed)

    v = Vina(sf_name="vina", seed=int(seed), verbosity=0)
    v.set_receptor(receptor_path)
    v.set_ligand_from_string(ligand_pdbqt)
    v.compute_vina_maps(center=center, box_size=size)
    v.dock(exhaustiveness=EXHAUSTIVENESS, n_poses=N_POSES)
    energies = v.energies(n_poses=1)
    return float(energies[0][0])


async def _persist(
    session: AsyncSession,
    experiment: Experiment,
    compound: Compound,
    target: Target,
    affinity: float,
    center: list[float],
    size: list[float],
) -> None:
    """Write the DockingResult for this (experiment, compound), replacing any prior row.

    Deleting the prior row keeps the channel idempotent across pipeline re-runs (the
    pipeline does not clear docking rows itself). Rows are flushed, not committed, so
    they live or die with the pipeline's transaction.
    """
    await session.execute(
        delete(DockingResult).where(
            DockingResult.experiment_id == experiment.id,
            DockingResult.compound_id == compound.id,
        )
    )
    session.add(
        DockingResult(
            experiment_id=experiment.id,
            compound_id=compound.id,
            target_id=target.id,
            binding_affinity=affinity,
            box_used={"center": center, "size": size, "source": target.box_source},
        )
    )
    await session.flush()


async def score(
    session: AsyncSession, experiment: Experiment, compound: Compound
) -> float | None:
    """Best Vina binding affinity (kcal/mol) for ``compound`` against the experiment target.

    Raises ``AdapterUnavailable`` when the target, its curated box, the Vina binary, or
    the prepared receptor is missing, or when the docking stack itself is unavailable.
    """
    if experiment.target_id is None:
        raise AdapterUnavailable("experiment has no target to dock against")

    target = await session.get(Target, experiment.target_id)
    if target is None:
        raise AdapterUnavailable(f"target {experiment.target_id} not found")

    center, size = _resolve_box(target)

    settings = get_settings()
    if not (settings.vina_binary or "").strip():
        raise AdapterUnavailable("vina_binary is not configured")

    receptor = _receptor_path(settings.data_dir, target.pdb_id)
    if receptor is None or not receptor.is_file():
        raise AdapterUnavailable(
            f"prepared receptor PDBQT not found for target {target.pdb_id!r}"
        )

    try:
        affinity = await asyncio.to_thread(
            _dock, str(receptor), compound.smiles, center, size, experiment.seed
        )
    except AdapterUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 — any vina/meeko/rdkit failure => unavailable
        raise AdapterUnavailable(
            f"docking failed for compound {compound.id}: {exc}"
        ) from exc

    await _persist(session, experiment, compound, target, affinity, center, size)
    log.info(
        "docked compound %s into target %s: %.2f kcal/mol",
        compound.id,
        target.id,
        affinity,
    )
    return affinity
