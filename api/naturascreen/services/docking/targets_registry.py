"""Hand-curated cancer protein targets with docking search boxes.

Each entry is a well-characterized, druggable cancer target whose binding pocket is
defined by a co-crystallized inhibitor in a real PDB structure. The ``box_center`` /
``box_size`` (Ångström) are taken from published AutoDock Vina docking studies of that
exact structure, and ``box_source`` records the provenance so the box is auditable
rather than fabricated. Where a source derives the center from a pocket predictor or a
non-cubic box, that is stated and the value is flagged approximate — it should be
re-derived against the prepared receptor during offline curation.

These boxes are the contract the docking adapter enforces: a target is only docked when
``dockable`` is set and all six box fields are populated, because a wrong or absent box
yields confident garbage.
"""

from __future__ import annotations

from typing import TypedDict


class TargetEntry(TypedDict):
    gene: str
    pdb_id: str
    description: str
    box_center: tuple[float, float, float]
    box_size: tuple[float, float, float]
    box_source: str


TARGETS: list[TargetEntry] = [
    {
        "gene": "EGFR",
        "pdb_id": "1M17",
        "description": (
            "Epidermal growth factor receptor tyrosine-kinase domain. ATP-competitive "
            "4-anilinoquinazoline pocket (erlotinib site); driver in NSCLC and other "
            "carcinomas."
        ),
        "box_center": (23.0, 0.0, 56.0),
        "box_size": (30.0, 30.0, 30.0),
        "box_source": (
            "ATP pocket of the EGFR kinase domain, box centered on the co-crystallized "
            "erlotinib in PDB 1M17. Center (23.0, 0.0, 56.0) Å and 30 Å cubic box from "
            "Unraveling potential EGFR kinase inhibitors, PMC12064201 (2024)."
        ),
    },
    {
        "gene": "ABL1",
        "pdb_id": "2HYY",
        "description": (
            "ABL1 (BCR-ABL) kinase domain. ATP pocket targeted by imatinib; driver of "
            "chronic myeloid leukemia."
        ),
        "box_center": (17.907, 59.987, 43.669),
        "box_size": (20.0, 20.0, 20.0),
        "box_source": (
            "ATP pocket of the ABL1 kinase domain, box defined on the imatinib position "
            "in PDB 2HYY. Center (17.907, 59.987, 43.669) Å and 20 Å cubic box from RSC "
            "Adv. 2025, DOI:10.1039/D4RA08330J (redocked imatinib RMSD < 2 Å)."
        ),
    },
    {
        "gene": "KDR",
        "pdb_id": "4ASD",
        "description": (
            "Vascular endothelial growth factor receptor 2 (VEGFR-2 / KDR) kinase "
            "domain. Type-II (DFG-out) pocket co-crystallized with sorafenib; central "
            "to tumor angiogenesis."
        ),
        "box_center": (24.2, 21.5, 34.8),
        "box_size": (20.0, 20.0, 20.0),
        "box_source": (
            "VEGFR-2 kinase domain co-crystallized with sorafenib in PDB 4ASD; box on "
            "PrankWeb Pocket 1. Center (24.2, 21.5, 34.8) Å and 20 Å cubic box from Sci. "
            "Rep. 2026, s41598-026-41232-9 (sorafenib redock RMSD ~1.0-1.2 Å). "
            "Approximate — refine against the prepared receptor."
        ),
    },
    {
        "gene": "HSP90AA1",
        "pdb_id": "1YET",
        "description": (
            "Heat-shock protein 90-alpha, N-terminal domain. ATP/geldanamycin pocket; "
            "chaperone whose inhibition destabilizes many oncogenic client proteins."
        ),
        "box_center": (33.934, -47.5359, 61.6928),
        "box_size": (43.0922, 46.3722, 56.9586),
        "box_source": (
            "N-terminal ATP/geldanamycin pocket of HSP90-alpha in PDB 1YET. Center "
            "(33.934, -47.5359, 61.6928) Å and box (43.09, 46.37, 56.96) Å from In Silico "
            "Docking Studies, BJSTR MS.ID.001149 (AutoDock Vina, exhaustiveness 8). "
            "Approximate, non-cubic box — refine against the prepared receptor."
        ),
    },
]
