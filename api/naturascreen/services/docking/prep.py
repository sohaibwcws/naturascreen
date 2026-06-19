"""Ligand preparation: SMILES -> 3D RDKit molecule -> AutoDock PDBQT (Meeko).

RDKit and Meeko are imported lazily inside :func:`prepare_ligand` so that importing
this module (and the docking adapter that depends on it) never pulls in the heavy
chemistry stack. The adapter converts any failure raised here into
``AdapterUnavailable`` so a missing tool or an awkward ligand degrades the binding
channel to "unavailable" rather than crashing the pipeline.
"""

from __future__ import annotations

# A fixed default so the embedded conformer is reproducible run-to-run; the adapter
# overrides it with the experiment seed.
DEFAULT_EMBED_SEED = 0xF00D


def prepare_ligand(smiles: str, *, seed: int = DEFAULT_EMBED_SEED) -> str:
    """Return an AutoDock PDBQT string for ``smiles``.

    Parses the SMILES, adds explicit hydrogens, embeds a single 3D conformer
    (deterministic for a given ``seed``), MMFF-minimizes it, and serializes with
    Meeko. Raises ``ValueError`` if RDKit cannot parse/embed the molecule or Meeko
    cannot write a valid PDBQT; the caller is responsible for translating that into
    ``AdapterUnavailable``.
    """
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from meeko import MoleculePreparation, PDBQTWriterLegacy

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"RDKit could not parse SMILES: {smiles!r}")

    mol = Chem.AddHs(mol)

    params = AllChem.ETKDGv3()
    params.randomSeed = int(seed)
    if AllChem.EmbedMolecule(mol, params) != 0:
        # Awkward ligands (macrocycles, cages) sometimes fail distance-geometry
        # embedding; fall back to random coordinates before giving up.
        if AllChem.EmbedMolecule(mol, useRandomCoords=True, randomSeed=int(seed)) != 0:
            raise ValueError(f"RDKit could not embed a 3D conformer for {smiles!r}")

    # Geometry refinement is best-effort: a non-converged minimization still leaves a
    # usable conformer, so a force-field hiccup must not sink the whole ligand.
    try:
        AllChem.MMFFOptimizeMolecule(mol)
    except Exception:  # noqa: BLE001 — optional refinement; embedded conformer stands
        pass

    preparator = MoleculePreparation()
    setups = preparator.prepare(mol)
    if not setups:
        raise ValueError(f"Meeko produced no molecule setup for {smiles!r}")

    pdbqt_string, is_ok, error_msg = PDBQTWriterLegacy.write_string(setups[0])
    if not is_ok or not pdbqt_string:
        raise ValueError(f"Meeko failed to write PDBQT for {smiles!r}: {error_msg}")
    return pdbqt_string
