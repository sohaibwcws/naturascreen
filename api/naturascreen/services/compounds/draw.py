"""2D structure depiction as SVG (RDKit). Used by the compound browser detail view.

Dark-theme aware: transparent background, light bonds/atoms to sit on the app surface.
"""

from __future__ import annotations


def draw_svg(smiles: str, *, width: int = 360, height: int = 240) -> str | None:
    """Render a SMILES to an SVG string, or None if RDKit cannot parse it."""
    from rdkit import Chem
    from rdkit.Chem.Draw import rdMolDraw2D

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    opts = drawer.drawOptions()
    opts.clearBackground = False  # transparent — inherit the dark panel
    opts.setBackgroundColour((0, 0, 0, 0))
    # Monochrome light palette so every atom/bond reads on the dark panel.
    light = (0.9, 0.93, 0.96)
    opts.setAtomPalette({-1: light})
    opts.bondLineWidth = 1
    rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    return drawer.GetDrawingText()
