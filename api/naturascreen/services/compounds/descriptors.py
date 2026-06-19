"""RDKit descriptor + fingerprint computation for one compound.

Outputs feed two consumers:
- the response model's feature vector (scalar physicochemical descriptors), and
- the applicability-domain check (spec §5), which needs the ECFP4 fingerprint. We persist
  the fingerprint's on-bit indices so the Tanimoto-to-training-set distance can be computed
  later without re-parsing SMILES.

Imported only where RDKit is available (ingestion / worker); kept out of the dependency-light
core test path.
"""

from __future__ import annotations

ECFP_RADIUS = 2
ECFP_NBITS = 2048


def compute(smiles: str) -> tuple[str | None, dict] | None:
    """Return (inchikey, descriptors) for a valid SMILES, or None if RDKit rejects it."""
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, Lipinski, QED, rdFingerprintGenerator

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    gen = rdFingerprintGenerator.GetMorganGenerator(radius=ECFP_RADIUS, fpSize=ECFP_NBITS)
    fp = gen.GetFingerprint(mol)

    try:
        inchikey = Chem.MolToInchiKey(mol) or None
    except Exception:
        inchikey = None

    descriptors = {
        "molecular_weight": round(Descriptors.MolWt(mol), 3),
        "logp": round(Crippen.MolLogP(mol), 3),
        "tpsa": round(Descriptors.TPSA(mol), 3),
        "h_bond_donors": Lipinski.NumHDonors(mol),
        "h_bond_acceptors": Lipinski.NumHAcceptors(mol),
        "rotatable_bonds": Lipinski.NumRotatableBonds(mol),
        "aromatic_rings": Lipinski.NumAromaticRings(mol),
        "fraction_csp3": round(Lipinski.FractionCSP3(mol), 4),
        "heavy_atoms": mol.GetNumHeavyAtoms(),
        "qed": round(QED.qed(mol), 4),
        "ecfp4_onbits": list(fp.GetOnBits()),
        "ecfp4_nbits": ECFP_NBITS,
    }
    return inchikey, descriptors


# Scalar feature order shared with the response model (spec §5). The fingerprint fields
# are excluded; they are used for the applicability-domain distance, not as model features.
FEATURE_KEYS: tuple[str, ...] = (
    "molecular_weight",
    "logp",
    "tpsa",
    "h_bond_donors",
    "h_bond_acceptors",
    "rotatable_bonds",
    "aromatic_rings",
    "fraction_csp3",
    "heavy_atoms",
    "qed",
)
